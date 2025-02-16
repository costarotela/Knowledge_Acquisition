"""
Gestor de caché para resultados de búsqueda de paquetes turísticos.

Implementa un sistema de caché con:
1. TTL (Time To Live) configurable
2. Invalidación por cambio de precio
3. Compresión de datos para optimizar memoria
4. Limpieza automática de entradas antiguas
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import zlib
import base64
import logging
from dataclasses import asdict
from .schemas import TravelPackage

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Gestor de caché con soporte para:
    - Almacenamiento en memoria con TTL
    - Compresión de datos
    - Invalidación selectiva
    - Estadísticas de uso
    """
    
    def __init__(
        self,
        ttl_minutes: int = 30,
        max_entries: int = 1000,
        compression_level: int = 6
    ):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_entries = max_entries
        self.compression_level = compression_level
        self.cache: Dict[str, Dict] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0
        }
        
    def _generate_key(self, provider: str, params: Dict) -> str:
        """Genera una clave única para los parámetros de búsqueda."""
        # Ordenamos los parámetros para asegurar consistencia
        sorted_params = json.dumps(params, sort_keys=True)
        return f"{provider}:{sorted_params}"
    
    def _compress_data(self, data: List[Dict]) -> str:
        """Comprime los datos usando zlib y los codifica en base64."""
        json_str = json.dumps([asdict(pkg) for pkg in data])
        compressed = zlib.compress(
            json_str.encode('utf-8'),
            level=self.compression_level
        )
        return base64.b64encode(compressed).decode('utf-8')
    
    def _decompress_data(self, compressed_data: str) -> List[Dict]:
        """Descomprime datos desde base64 y zlib."""
        decoded = base64.b64decode(compressed_data.encode('utf-8'))
        decompressed = zlib.decompress(decoded)
        return json.loads(decompressed.decode('utf-8'))
    
    def _is_valid(self, entry: Dict) -> bool:
        """Verifica si una entrada de caché sigue siendo válida."""
        if not entry:
            return False
            
        # Verificar TTL
        cached_time = datetime.fromisoformat(entry['timestamp'])
        if datetime.now() - cached_time > self.ttl:
            return False
            
        return True
    
    def _cleanup_old_entries(self):
        """Limpia entradas antiguas si se supera el límite."""
        if len(self.cache) <= self.max_entries:
            return
            
        # Ordenar por timestamp y eliminar las más antiguas
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: datetime.fromisoformat(x[1]['timestamp'])
        )
        
        # Mantener solo las más recientes
        entries_to_remove = len(self.cache) - self.max_entries
        for key, _ in sorted_entries[:entries_to_remove]:
            del self.cache[key]
            
        logger.info(f"Limpiadas {entries_to_remove} entradas antiguas del caché")
    
    def get(
        self,
        provider: str,
        search_params: Dict
    ) -> Optional[List[TravelPackage]]:
        """
        Recupera resultados del caché si existen y son válidos.
        
        Args:
            provider: Nombre del proveedor
            search_params: Parámetros de búsqueda
            
        Returns:
            Lista de paquetes o None si no hay caché válido
        """
        cache_key = self._generate_key(provider, search_params)
        cached_entry = self.cache.get(cache_key)
        
        if not cached_entry or not self._is_valid(cached_entry):
            self.stats["misses"] += 1
            return None
            
        self.stats["hits"] += 1
        
        # Descomprimir y reconstruir objetos
        raw_data = self._decompress_data(cached_entry['data'])
        return [TravelPackage(**pkg_data) for pkg_data in raw_data]
    
    def set(
        self,
        provider: str,
        search_params: Dict,
        packages: List[TravelPackage]
    ):
        """
        Almacena resultados en el caché.
        
        Args:
            provider: Nombre del proveedor
            search_params: Parámetros de búsqueda
            packages: Lista de paquetes a almacenar
        """
        cache_key = self._generate_key(provider, search_params)
        
        # Comprimir datos
        compressed_data = self._compress_data(packages)
        
        # Almacenar con metadata
        self.cache[cache_key] = {
            'timestamp': datetime.now().isoformat(),
            'data': compressed_data,
            'provider': provider,
            'params': search_params
        }
        
        self._cleanup_old_entries()
    
    def invalidate(
        self,
        provider: Optional[str] = None,
        search_params: Optional[Dict] = None
    ):
        """
        Invalida entradas específicas del caché.
        
        Args:
            provider: Si se especifica, solo invalida este proveedor
            search_params: Si se especifica, solo invalida estas búsquedas
        """
        keys_to_remove = []
        
        for key, entry in self.cache.items():
            should_remove = False
            
            if provider and entry['provider'] == provider:
                should_remove = True
            elif search_params:
                # Verificar si los parámetros coinciden
                cached_params = entry['params']
                if all(
                    cached_params.get(k) == v 
                    for k, v in search_params.items()
                ):
                    should_remove = True
                    
            if should_remove:
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.cache[key]
            
        self.stats["invalidations"] += len(keys_to_remove)
        
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del uso del caché."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_ratio = (
            self.stats["hits"] / total_requests 
            if total_requests > 0 else 0
        )
        
        return {
            **self.stats,
            "total_entries": len(self.cache),
            "hit_ratio": hit_ratio,
            "memory_usage": sum(
                len(entry['data']) 
                for entry in self.cache.values()
            )
        }
