"""
Gestor de almacenamiento persistente usando Supabase.

Este módulo maneja:
1. Almacenamiento de paquetes y presupuestos
2. Sistema RAG para aprendizaje continuo
3. Caché y recuperación eficiente
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import asyncio
from supabase import create_client, Client
from langchain.vectorstores import SupabaseVectorStore
from langchain.embeddings import OpenAIEmbeddings
from .schemas import TravelPackage, Budget, SalesQuery

class StorageManager:
    """Gestor de almacenamiento con capacidades RAG."""
    
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        openai_key: str,
        embedding_model: str = "text-embedding-3-small"
    ):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=openai_key
        )
        self.vector_store = SupabaseVectorStore(
            self.supabase,
            self.embeddings,
            table_name="travel_embeddings"
        )
        self.logger = logging.getLogger(__name__)

    async def store_package(self, package: TravelPackage) -> str:
        """
        Almacena un paquete y genera sus embeddings.
        
        Args:
            package: Paquete a almacenar
            
        Returns:
            ID del paquete almacenado
        """
        # Convertir a formato para embeddings
        package_text = f"""
        Destino: {package.destination}
        Precio: {package.price}
        Duración: {package.duration}
        Incluye: {', '.join(package.includes)}
        Temporada: {package.season}
        """
        
        # Generar embedding
        try:
            embedding = await self.embeddings.aembed_query(package_text)
            
            # Almacenar en Supabase
            result = await self.supabase.table("travel_packages").insert({
                "data": package.dict(),
                "embedding": embedding,
                "created_at": datetime.now().isoformat()
            }).execute()
            
            return result.data[0]["id"]
            
        except Exception as e:
            self.logger.error(f"Error al almacenar paquete: {e}")
            raise

    async def store_budget(self, budget: Budget) -> str:
        """
        Almacena un presupuesto completo.
        
        Args:
            budget: Presupuesto a almacenar
            
        Returns:
            ID del presupuesto
        """
        try:
            result = await self.supabase.table("budgets").insert({
                "data": budget.dict(),
                "created_at": datetime.now().isoformat(),
                "status": "pending"
            }).execute()
            
            return result.data[0]["id"]
            
        except Exception as e:
            self.logger.error(f"Error al almacenar presupuesto: {e}")
            raise

    async def find_similar_packages(
        self,
        query: SalesQuery,
        limit: int = 5
    ) -> List[TravelPackage]:
        """
        Busca paquetes similares usando RAG.
        
        Args:
            query: Consulta de búsqueda
            limit: Número máximo de resultados
            
        Returns:
            Lista de paquetes similares
        """
        query_text = f"""
        Destino: {query.destination}
        Presupuesto: {query.budget}
        Duración: {query.duration}
        Preferencias: {', '.join(query.preferences)}
        """
        
        try:
            results = await self.vector_store.asimilarity_search_with_score(
                query_text,
                k=limit
            )
            
            packages = []
            for doc, score in results:
                if score > 0.7:  # Umbral de similitud
                    packages.append(TravelPackage(**doc.metadata))
                    
            return packages
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda RAG: {e}")
            raise

    async def update_budget_status(
        self,
        budget_id: str,
        status: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Actualiza el estado de un presupuesto.
        
        Args:
            budget_id: ID del presupuesto
            status: Nuevo estado
            metadata: Metadatos adicionales
        """
        try:
            await self.supabase.table("budgets").update({
                "status": status,
                "metadata": metadata,
                "updated_at": datetime.now().isoformat()
            }).eq("id", budget_id).execute()
            
        except Exception as e:
            self.logger.error(f"Error al actualizar presupuesto: {e}")
            raise
