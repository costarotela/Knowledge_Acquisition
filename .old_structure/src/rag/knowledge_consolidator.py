from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import asyncio
from pydantic import BaseModel, Field
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from ..embeddings.vector_store import VectorStore, VectorDocument
from ..scrapers.providers.advanced_crawler import AdvancedCrawler
from ..scrapers.providers.youtube_scraper import YouTubeScraper

class KnowledgeNode(BaseModel):
    """Modelo para un nodo de conocimiento."""
    id: str
    content: str
    source_type: str  # web, youtube, etc.
    source_url: str
    confidence: float
    last_validated: datetime
    related_nodes: Set[str] = Field(default_factory=set)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    validation_history: List[Dict[str, Any]] = Field(default_factory=list)

class KnowledgeGraph(BaseModel):
    """Modelo para el grafo de conocimiento."""
    nodes: Dict[str, KnowledgeNode] = Field(default_factory=dict)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeConsolidator:
    """
    Sistema para consolidar y validar conocimiento de múltiples fuentes.
    
    Este sistema:
    1. Recopila información de múltiples fuentes
    2. Valida y verifica la información
    3. Detecta y resuelve conflictos
    4. Genera resúmenes y conclusiones
    5. Mantiene un grafo de conocimiento
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4",
        temperature: float = 0.7,
        vector_store: Optional[VectorStore] = None
    ):
        """Inicializa el consolidador de conocimiento."""
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature
        )
        self.vector_store = vector_store or VectorStore("consolidated_knowledge")
        self.knowledge_graph = KnowledgeGraph()
        self.crawler = AdvancedCrawler()
        self.youtube_scraper = YouTubeScraper()
        
        # Prompt para validación de conocimiento
        self.validation_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en validación de conocimiento. Tu tarea es:
            1. Verificar la coherencia y precisión de la información
            2. Detectar posibles contradicciones o conflictos
            3. Evaluar la calidad y confiabilidad de las fuentes
            4. Asignar un nivel de confianza (0-1)
            
            Información a validar:
            {content}
            
            Fuente: {source}
            Tipo: {source_type}
            
            Información relacionada:
            {related_info}
            """),
        ])
        
        # Prompt para síntesis de conocimiento
        self.synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en síntesis de conocimiento. Tu tarea es:
            1. Integrar información de múltiples fuentes
            2. Identificar patrones y relaciones
            3. Generar conclusiones
            4. Proponer nuevas áreas de investigación
            
            Información disponible:
            {knowledge_nodes}
            
            Genera una síntesis que incluya:
            1. Principales hallazgos
            2. Relaciones identificadas
            3. Áreas de incertidumbre
            4. Recomendaciones para investigación adicional
            """),
        ])
        
        self.validation_chain = LLMChain(
            llm=self.llm,
            prompt=self.validation_prompt
        )
        
        self.synthesis_chain = LLMChain(
            llm=self.llm,
            prompt=self.synthesis_prompt
        )
    
    async def add_knowledge(
        self,
        content: str,
        source_url: str,
        source_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeNode:
        """Agrega nuevo conocimiento al sistema."""
        # Buscar información relacionada
        related_docs = await self.vector_store.search(
            content,
            k=5,
            threshold=0.7
        )
        
        # Validar el conocimiento
        validation_result = await self.validation_chain.arun({
            "content": content,
            "source": source_url,
            "source_type": source_type,
            "related_info": "\n".join(
                f"- {doc['content']}" for doc in related_docs
            )
        })
        
        # Crear nodo de conocimiento
        node = KnowledgeNode(
            id=f"node_{len(self.knowledge_graph.nodes)}",
            content=content,
            source_type=source_type,
            source_url=source_url,
            confidence=float(validation_result.get("confidence", 0.5)),
            last_validated=datetime.now(),
            metadata=metadata or {},
            validation_history=[{
                "timestamp": datetime.now().isoformat(),
                "validation_result": validation_result
            }]
        )
        
        # Agregar al grafo
        self.knowledge_graph.nodes[node.id] = node
        
        # Conectar con nodos relacionados
        for doc in related_docs:
            if doc.get("metadata", {}).get("node_id") in self.knowledge_graph.nodes:
                node.related_nodes.add(doc["metadata"]["node_id"])
                self.knowledge_graph.edges.append({
                    "source": node.id,
                    "target": doc["metadata"]["node_id"],
                    "weight": doc["score"]
                })
        
        # Almacenar en vector store
        await self.vector_store.add_documents([
            VectorDocument(
                content=content,
                metadata={
                    "node_id": node.id,
                    "source_type": source_type,
                    "source_url": source_url,
                    **metadata or {}
                }
            )
        ])
        
        return node
    
    async def consolidate_knowledge(
        self,
        topic: Optional[str] = None,
        min_confidence: float = 0.7
    ) -> Dict[str, Any]:
        """
        Consolida el conocimiento existente y genera conclusiones.
        
        Args:
            topic: Tema específico para consolidar, o None para todo
            min_confidence: Confianza mínima para incluir nodos
        
        Returns:
            Diccionario con conclusiones y metadatos
        """
        # Filtrar nodos relevantes
        relevant_nodes = {
            node_id: node
            for node_id, node in self.knowledge_graph.nodes.items()
            if node.confidence >= min_confidence and (
                not topic or
                topic.lower() in node.content.lower() or
                any(topic.lower() in meta_value.lower()
                    for meta_value in node.metadata.values()
                    if isinstance(meta_value, str))
            )
        }
        
        if not relevant_nodes:
            return {
                "status": "error",
                "message": "No se encontraron nodos relevantes"
            }
        
        # Generar síntesis
        synthesis = await self.synthesis_chain.arun({
            "knowledge_nodes": "\n\n".join(
                f"[{node_id}] {node.content}\n"
                f"Fuente: {node.source_url}\n"
                f"Confianza: {node.confidence}"
                for node_id, node in relevant_nodes.items()
            )
        })
        
        # Actualizar metadatos del grafo
        self.knowledge_graph.metadata.update({
            "last_consolidation": datetime.now().isoformat(),
            "total_nodes": len(self.knowledge_graph.nodes),
            "consolidated_nodes": len(relevant_nodes),
            "average_confidence": sum(
                node.confidence for node in relevant_nodes.values()
            ) / len(relevant_nodes)
        })
        
        return {
            "status": "success",
            "synthesis": synthesis,
            "metadata": self.knowledge_graph.metadata,
            "consolidated_nodes": len(relevant_nodes),
            "timestamp": datetime.now().isoformat()
        }
    
    async def validate_and_update(
        self,
        node_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Revalida y actualiza nodos de conocimiento.
        
        Args:
            node_ids: Lista de IDs de nodos a validar, o None para todos
        
        Returns:
            Resultados de la validación
        """
        nodes_to_validate = (
            [self.knowledge_graph.nodes[nid] for nid in node_ids]
            if node_ids
            else list(self.knowledge_graph.nodes.values())
        )
        
        results = []
        for node in nodes_to_validate:
            # Obtener información relacionada actualizada
            related_docs = await self.vector_store.search(
                node.content,
                k=5,
                threshold=0.7
            )
            
            # Revalidar
            validation_result = await self.validation_chain.arun({
                "content": node.content,
                "source": node.source_url,
                "source_type": node.source_type,
                "related_info": "\n".join(
                    f"- {doc['content']}" for doc in related_docs
                )
            })
            
            # Actualizar nodo
            node.confidence = float(validation_result.get("confidence", node.confidence))
            node.last_validated = datetime.now()
            node.validation_history.append({
                "timestamp": datetime.now().isoformat(),
                "validation_result": validation_result
            })
            
            results.append({
                "node_id": node.id,
                "old_confidence": node.validation_history[-2]["validation_result"].get("confidence")
                if len(node.validation_history) > 1 else None,
                "new_confidence": node.confidence,
                "validation_result": validation_result
            })
        
        return {
            "status": "success",
            "validated_nodes": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del conocimiento almacenado."""
        nodes = self.knowledge_graph.nodes.values()
        return {
            "total_nodes": len(nodes),
            "average_confidence": sum(n.confidence for n in nodes) / len(nodes)
            if nodes else 0,
            "source_types": {
                source_type: len([n for n in nodes if n.source_type == source_type])
                for source_type in {n.source_type for n in nodes}
            },
            "nodes_by_confidence": {
                "high": len([n for n in nodes if n.confidence >= 0.8]),
                "medium": len([n for n in nodes if 0.5 <= n.confidence < 0.8]),
                "low": len([n for n in nodes if n.confidence < 0.5])
            },
            "last_validation": max(
                (n.last_validated for n in nodes),
                default=None
            ),
            "vector_store": self.vector_store.get_collection_stats()
        }
