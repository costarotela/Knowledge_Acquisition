"""
Implementación de almacenamiento usando Supabase.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import numpy as np
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
import json
import os
from dotenv import load_dotenv

from ..models.knowledge_models import (
    KnowledgeItem,
    KnowledgeFragment,
    KnowledgeQuery,
    SearchResult,
    ContentType
)

logger = logging.getLogger(__name__)

class SupabaseStorage:
    """Almacenamiento vectorial usando Supabase."""
    
    def __init__(self, 
                 embeddings_model: str = "all-MiniLM-L6-v2",
                 embedding_dimension: int = 384):
        """
        Inicializa el almacenamiento.
        
        Args:
            embeddings_model: Modelo de SentenceTransformers a usar
            embedding_dimension: Dimensión de los embeddings
        """
        load_dotenv()
        
        # Configuración de Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_KEY son requeridos")
            
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.encoder = SentenceTransformer(embeddings_model)
        self.embedding_dimension = embedding_dimension
        
    async def store_item(self, item: KnowledgeItem) -> str:
        """
        Almacena un item de conocimiento.
        
        Args:
            item: KnowledgeItem a almacenar
            
        Returns:
            ID del item almacenado
        """
        try:
            # Generar embeddings para fragmentos que no los tengan
            for fragment in item.fragments:
                if not fragment.embedding:
                    # Para video, concatenamos el contenido con metadatos temporales
                    if item.source.content_type == ContentType.VIDEO:
                        temporal_context = f"Time: {fragment.start_time}-{fragment.end_time}. "
                        embedding_text = temporal_context + fragment.content
                    else:
                        embedding_text = fragment.content
                        
                    embedding = self.encoder.encode(embedding_text)
                    fragment.embedding = embedding.tolist()
            
            # Calcular métricas de calidad
            item.calculate_quality_metrics()
            
            # Preparar datos para Supabase
            item_data = {
                "source": item.source.dict(),
                "summary": item.summary,
                "main_topics": item.main_topics,
                "metadata": {
                    **item.metadata,
                    "duration": item.source.duration if item.source.content_type == ContentType.VIDEO else None,
                    "frame_rate": item.source.frame_rate if item.source.content_type == ContentType.VIDEO else None
                },
                "quality_metrics": item.quality_metrics,
                "processed_at": item.processed_at.isoformat(),
                "content_type": item.source.content_type
            }
            
            # Insertar item principal
            result = self.supabase.table("knowledge_items").insert(item_data).execute()
            item_id = result.data[0]["id"]
            
            # Insertar fragmentos en lotes para mejor rendimiento
            fragment_batch = []
            for fragment in item.fragments:
                fragment_data = {
                    "item_id": item_id,
                    "content": fragment.content,
                    "start_time": fragment.start_time,
                    "end_time": fragment.end_time,
                    "keywords": fragment.keywords,
                    "topics": fragment.topics,
                    "confidence_score": fragment.confidence_score,
                    "embedding": fragment.embedding,
                    "frame_count": fragment.frame_count if hasattr(fragment, 'frame_count') else None,
                    "scene_change": fragment.scene_change if hasattr(fragment, 'scene_change') else False
                }
                fragment_batch.append(fragment_data)
                
                # Insertar en lotes de 100
                if len(fragment_batch) >= 100:
                    self.supabase.table("knowledge_fragments").insert(fragment_batch).execute()
                    fragment_batch = []
            
            # Insertar fragmentos restantes
            if fragment_batch:
                self.supabase.table("knowledge_fragments").insert(fragment_batch).execute()
            
            # Insertar citaciones
            citation_batch = []
            for citation in item.citations:
                citation_data = {
                    "item_id": item_id,
                    "text": citation.text,
                    "source_url": citation.source_url,
                    "context": citation.context,
                    "page_number": citation.page_number,
                    "accessed_date": citation.accessed_date.isoformat(),
                    "timestamp": citation.timestamp if hasattr(citation, 'timestamp') else None
                }
                citation_batch.append(citation_data)
                
                if len(citation_batch) >= 100:
                    self.supabase.table("citations").insert(citation_batch).execute()
                    citation_batch = []
                    
            if citation_batch:
                self.supabase.table("citations").insert(citation_batch).execute()
                
            return item_id
            
        except Exception as e:
            logger.error(f"Error almacenando item: {str(e)}")
            raise
            
    async def search(self, query: KnowledgeQuery) -> List[SearchResult]:
        """
        Busca items de conocimiento.
        
        Args:
            query: KnowledgeQuery con parámetros de búsqueda
            
        Returns:
            Lista de SearchResult ordenados por relevancia
        """
        try:
            # Generar embedding de la consulta
            if not query.embedding:
                # Para búsquedas de video, podemos incluir contexto temporal
                if query.filters and query.filters.get("content_type") == "video":
                    time_range = query.filters.get("time_range", "")
                    if time_range:
                        query_text = f"Time: {time_range}. {query.query}"
                    else:
                        query_text = query.query
                else:
                    query_text = query.query
                    
                query.embedding = self.encoder.encode(query_text).tolist()
                
            # Búsqueda por similitud
            rpc_params = {
                "query_embedding": query.embedding,
                "match_threshold": query.min_confidence,
                "match_count": query.max_results,
                "filters": json.dumps({
                    **query.filters,
                    "time_range": query.filters.get("time_range", None) if query.filters else None
                })
            }
                
            results = self.supabase.rpc(
                "match_knowledge_fragments",
                rpc_params
            ).execute()
            
            # Procesar resultados
            search_results = []
            for match in results.data:
                # Obtener item completo
                item_result = self.supabase.table("knowledge_items")\
                    .select("*")\
                    .eq("id", match["item_id"])\
                    .execute()
                    
                if not item_result.data:
                    continue
                    
                item_data = item_result.data[0]
                
                # Reconstruir KnowledgeItem
                item = KnowledgeItem(
                    id=item_data["id"],
                    source=item_data["source"],
                    fragments=self._get_item_fragments(item_data["id"]),
                    summary=item_data["summary"],
                    main_topics=item_data["main_topics"],
                    metadata=item_data["metadata"],
                    quality_metrics=item_data["quality_metrics"],
                    processed_at=datetime.fromisoformat(item_data["processed_at"])
                )
                
                # Encontrar fragmentos relevantes
                matching_fragments = [
                    f for f in item.fragments 
                    if f.relevance_score and f.relevance_score >= query.min_confidence
                ]
                
                search_results.append(SearchResult(
                    item=item,
                    relevance_score=match["similarity"],
                    matching_fragments=matching_fragments,
                    context=self._build_context(matching_fragments)
                ))
                
            return sorted(search_results, 
                        key=lambda x: x.relevance_score, 
                        reverse=True)
                        
        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}")
            raise
            
    def _get_item_fragments(self, item_id: str) -> List[KnowledgeFragment]:
        """Obtiene todos los fragmentos de un item."""
        result = self.supabase.table("knowledge_fragments")\
            .select("*")\
            .eq("item_id", item_id)\
            .execute()
            
        return [KnowledgeFragment(**f) for f in result.data]
        
    def _build_context(self, fragments: List[KnowledgeFragment]) -> str:
        """Construye contexto a partir de fragmentos."""
        if not fragments:
            return ""
            
        # Ordenar por tiempo si es video
        if all(f.start_time is not None for f in fragments):
            fragments.sort(key=lambda x: x.start_time)
            
        return "\n...\n".join(f.content for f in fragments)
