from typing import Dict, List, Any, Optional
from datetime import datetime
import numpy as np
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
import logging
import json
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseKnowledgeBase:
    def __init__(self, embeddings_model: str = "all-MiniLM-L6-v2"):
        """
        Inicializa la base de conocimientos usando Supabase.
        
        Args:
            embeddings_model: Modelo de embeddings a usar
        """
        load_dotenv()
        
        # Inicializar cliente Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        logger.info(f"Usando Supabase URL: {supabase_url}")
        logger.info(f"Usando Supabase Key: {supabase_key[:10]}...")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_KEY deben estar definidos en .env")
            
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.encoder = SentenceTransformer(embeddings_model)
        
    def initialize_database(self):
        """
        Verifica que las tablas necesarias existen en Supabase.
        """
        tables_exist = True
        try:
            # Verificar si las tablas existen
            logger.info("Verificando tabla videos...")
            result = self.supabase.table('videos').select("count").execute()
            logger.info(f"Resultado videos: {result}")
            
        except Exception as e:
            logger.error(f"Error verificando tablas: {str(e)}")
            tables_exist = False
            
        if not tables_exist:
            logger.info("Creando tablas...")
            try:
                # Crear tabla de videos
                self.supabase.table('videos').insert({
                    'title': 'Test Video',
                    'channel': 'Test Channel',
                    'url': 'https://youtube.com/test',
                    'transcript': 'Test transcript',
                    'embedding': [0.0] * 384  # Dimensión del modelo all-MiniLM-L6-v2
                }).execute()
                logger.info("Tablas creadas exitosamente")
            except Exception as e:
                logger.error(f"Error creando tablas: {str(e)}")
                raise
    
    def store_video_knowledge(self, title: str, channel: str, url: str, transcript: str):
        """
        Almacena el conocimiento extraído de un video.
        
        Args:
            title: Título del video
            channel: Canal del video
            url: URL del video
            transcript: Transcripción del video
        """
        try:
            # Generar embedding para el transcript
            embedding = self.encoder.encode(transcript).tolist()
            
            # Insertar video
            result = self.supabase.table('videos').insert({
                'title': title,
                'channel': channel,
                'url': url,
                'transcript': transcript,
                'embedding': embedding
            }).execute()
            
            logger.info(f"Video almacenado: {title}")
            return result.data
            
        except Exception as e:
            logger.error(f"Error almacenando video: {str(e)}")
            raise
            
    def get_videos(self) -> List[Dict]:
        """
        Obtiene todos los videos almacenados.
        
        Returns:
            Lista de videos con sus datos
        """
        try:
            result = self.supabase.table('videos').select("*").execute()
            return result.data
            
        except Exception as e:
            logger.error(f"Error obteniendo videos: {str(e)}")
            return []
            
    def search_knowledge(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Busca conocimiento relevante para una pregunta.
        
        Args:
            query: Pregunta o consulta
            top_k: Número de resultados a retornar
            
        Returns:
            Lista de resultados ordenados por relevancia
        """
        try:
            # Generar embedding para la consulta
            query_embedding = self.encoder.encode(query).tolist()
            
            # Buscar videos similares usando match_vectors
            result = self.supabase.rpc(
                'match_videos',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': 0.3,  # Bajamos el umbral para ser menos estrictos
                    'match_count': top_k
                }
            ).execute()
            
            # Procesar resultados
            results = []
            for item in result.data:
                results.append({
                    'title': item['title'],
                    'channel': item['channel'],
                    'url': item['url'],
                    'context': item['transcript'],
                    'score': item['similarity']
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error buscando conocimiento: {str(e)}")
            raise
            
    def get_statistics(self) -> Dict:
        """
        Obtiene estadísticas de la base de conocimientos.
        
        Returns:
            Dict con estadísticas como total de videos, conceptos, etc.
        """
        try:
            # Obtener total de videos
            videos_result = self.supabase.table('videos').select("*", count='exact').execute()
            total_videos = len(videos_result.data) if videos_result.data else 0
            
            # Obtener fecha de última actualización
            if videos_result.data:
                latest_video = max(videos_result.data, key=lambda x: x['created_at'])
                last_update = latest_video['created_at']
            else:
                last_update = "N/A"
            
            # Obtener total de conceptos (por ahora igual a videos)
            total_concepts = total_videos
            
            return {
                "total_videos": total_videos,
                "total_concepts": total_concepts,
                "last_update": last_update
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            raise
