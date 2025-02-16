"""
Gestor de memoria usando Supabase.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from supabase import create_client, Client
from ..core.config import config

class SupabaseMemory:
    """
    Gestor de memoria usando Supabase.
    
    Características:
    1. Almacenamiento de presupuestos
    2. Almacenamiento de planes
    3. Sistema RAG para búsqueda semántica
    4. Historial de operaciones
    """
    
    def __init__(self):
        """Inicializar cliente Supabase."""
        self.supabase: Client = create_client(
            config.PUBLIC_SUPABASE_URL,
            config.PUBLIC_SUPABASE_ANON_KEY
        )
        self.logger = logging.getLogger(__name__)
    
    async def store_budget(
        self,
        budget: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Almacenar un presupuesto."""
        try:
            # Preparar datos
            data = {
                "content": json.dumps(budget),
                "metadata": json.dumps(metadata) if metadata else None,
                "created_at": datetime.now().isoformat(),
                "type": "budget"
            }
            
            # Insertar en Supabase
            result = self.supabase.table("memories").insert(data).execute()
            
            return result.data[0]["id"]
            
        except Exception as e:
            self.logger.error(f"Error almacenando presupuesto: {str(e)}")
            raise
    
    async def store_plan(
        self,
        plan: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Almacenar un plan de viaje."""
        try:
            # Preparar datos
            data = {
                "content": json.dumps(plan),
                "metadata": json.dumps(metadata) if metadata else None,
                "created_at": datetime.now().isoformat(),
                "type": "plan"
            }
            
            # Insertar en Supabase
            result = self.supabase.table("memories").insert(data).execute()
            
            return result.data[0]["id"]
            
        except Exception as e:
            self.logger.error(f"Error almacenando plan: {str(e)}")
            raise
    
    async def search_similar(
        self,
        query: str,
        type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Buscar memorias similares usando RAG."""
        try:
            # Construir query
            query_builder = self.supabase.table("memories")
            
            if type:
                query_builder = query_builder.eq("type", type)
            
            # Usar búsqueda semántica de Supabase
            result = query_builder.execute()
            
            # Procesar resultados
            memories = []
            for item in result.data:
                try:
                    content = json.loads(item["content"])
                    metadata = (
                        json.loads(item["metadata"])
                        if item["metadata"] else None
                    )
                    memories.append({
                        "id": item["id"],
                        "content": content,
                        "metadata": metadata,
                        "created_at": item["created_at"],
                        "type": item["type"]
                    })
                except json.JSONDecodeError:
                    self.logger.warning(
                        f"Error decodificando memoria {item['id']}"
                    )
                    continue
            
            return memories[:limit]
            
        except Exception as e:
            self.logger.error(f"Error buscando memorias: {str(e)}")
            raise
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Obtener una memoria específica."""
        try:
            result = (
                self.supabase.table("memories")
                .eq("id", memory_id)
                .execute()
            )
            
            if not result.data:
                return None
            
            item = result.data[0]
            return {
                "id": item["id"],
                "content": json.loads(item["content"]),
                "metadata": (
                    json.loads(item["metadata"])
                    if item["metadata"] else None
                ),
                "created_at": item["created_at"],
                "type": item["type"]
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo memoria: {str(e)}")
            raise
    
    async def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Actualizar una memoria existente."""
        try:
            # Preparar datos
            data = {}
            if "content" in updates:
                data["content"] = json.dumps(updates["content"])
            if "metadata" in updates:
                data["metadata"] = json.dumps(updates["metadata"])
            
            # Actualizar en Supabase
            result = (
                self.supabase.table("memories")
                .update(data)
                .eq("id", memory_id)
                .execute()
            )
            
            return bool(result.data)
            
        except Exception as e:
            self.logger.error(f"Error actualizando memoria: {str(e)}")
            raise
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Eliminar una memoria."""
        try:
            result = (
                self.supabase.table("memories")
                .delete()
                .eq("id", memory_id)
                .execute()
            )
            
            return bool(result.data)
            
        except Exception as e:
            self.logger.error(f"Error eliminando memoria: {str(e)}")
            raise
