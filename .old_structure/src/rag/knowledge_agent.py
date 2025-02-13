from typing import List, Dict, Any, Optional
import os
from datetime import datetime
from pydantic import BaseModel
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
from ..embeddings.vector_store import VectorStore
from ..scrapers.providers.advanced_crawler import AdvancedCrawler, CrawledPage

load_dotenv()

class KnowledgeQuery(BaseModel):
    """Modelo para consultas de conocimiento."""
    query: str
    context: Optional[str] = None
    metadata_filters: Optional[Dict[str, Any]] = None

class KnowledgeResponse(BaseModel):
    """Modelo para respuestas de conocimiento."""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    metadata: Dict[str, Any]

class KnowledgeAgent:
    """Agente de conocimiento con capacidades de RAG."""
    
    def __init__(
        self,
        model_name: str = "gpt-4",
        temperature: float = 0.7,
        vector_store: Optional[VectorStore] = None
    ):
        """Inicializa el agente de conocimiento."""
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.vector_store = vector_store or VectorStore()
        self.crawler = AdvancedCrawler()
        
        # Configurar el prompt para RAG
        self.rag_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente experto que proporciona respuestas precisas basadas en el contexto proporcionado.
            Usa solo la información del contexto y tu conocimiento general para responder.
            Si la información en el contexto es insuficiente, indícalo claramente.
            
            Contexto:
            {context}
            
            Pregunta: {query}
            """),
        ])
        
        self.rag_chain = LLMChain(
            llm=self.llm,
            prompt=self.rag_prompt
        )
    
    async def learn_from_url(self, url: str) -> CrawledPage:
        """Aprende de una URL crawleando y almacenando su contenido."""
        # Crawlear la página
        page = await self.crawler.scrape(url)
        
        # Almacenar chunks en el vector store
        await self.vector_store.add_documents([
            chunk for chunk in page.chunks
        ])
        
        return page
    
    async def learn_from_urls(self, urls: List[str]) -> List[CrawledPage]:
        """Aprende de múltiples URLs."""
        pages = await self.crawler.scrape_multiple(urls)
        
        # Almacenar todos los chunks
        for page in pages:
            await self.vector_store.add_documents([
                chunk for chunk in page.chunks
            ])
        
        return pages
    
    async def query_knowledge(
        self,
        query: KnowledgeQuery,
        k: int = 5
    ) -> KnowledgeResponse:
        """
        Consulta la base de conocimiento usando RAG.
        
        Args:
            query: Consulta de conocimiento
            k: Número de documentos a recuperar
        
        Returns:
            Respuesta generada con fuentes y metadata
        """
        # Buscar documentos relevantes
        relevant_docs = await self.vector_store.search(
            query.query,
            k=k,
            threshold=0.7
        )
        
        if not relevant_docs:
            return KnowledgeResponse(
                answer="Lo siento, no encontré información relevante para responder tu pregunta.",
                sources=[],
                confidence=0.0,
                metadata={"found_documents": 0}
            )
        
        # Construir contexto
        context = "\n\n".join([
            f"[Fuente {i+1}]\n{doc['content']}"
            for i, doc in enumerate(relevant_docs)
        ])
        
        if query.context:
            context = f"{query.context}\n\n{context}"
        
        # Generar respuesta
        response = await self.rag_chain.arun({
            "context": context,
            "query": query.query
        })
        
        # Calcular confianza basada en scores de similitud
        confidence = sum(doc["score"] for doc in relevant_docs) / len(relevant_docs)
        
        return KnowledgeResponse(
            answer=response,
            sources=relevant_docs,
            confidence=confidence,
            metadata={
                "found_documents": len(relevant_docs),
                "average_similarity": confidence,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del agente."""
        return {
            "vector_store": self.vector_store.get_collection_stats(),
            "model": {
                "name": self.llm.model_name,
                "temperature": self.llm.temperature
            },
            "timestamp": datetime.now().isoformat()
        }
