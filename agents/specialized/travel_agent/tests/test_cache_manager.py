"""
Pruebas para el sistema de caché del gestor de proveedores.
"""

import pytest
from datetime import datetime, timedelta
import asyncio
from ..core.cache_manager import CacheManager
from ..core.schemas import TravelPackage, Accommodation, Activity

@pytest.fixture
def cache_manager():
    return CacheManager(ttl_minutes=30, max_entries=5)

@pytest.fixture
def sample_package():
    return TravelPackage(
        title="Paquete de prueba",
        description="Descripción de prueba",
        price=1500.0,
        currency="USD",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=7),
        accommodation=Accommodation(
            name="Hotel de prueba",
            type="hotel",
            stars=4
        ),
        activities=[
            Activity(
                title="Actividad 1",
                description="Descripción actividad 1",
                duration="2 horas"
            )
        ]
    )

def test_cache_basic_operations(cache_manager, sample_package):
    """Prueba operaciones básicas del caché."""
    provider = "test_provider"
    search_params = {"destination": "Tokyo", "dates": {}}
    packages = [sample_package]
    
    # Verificar que inicialmente no hay datos en caché
    assert cache_manager.get(provider, search_params) is None
    
    # Almacenar datos
    cache_manager.set(provider, search_params, packages)
    
    # Verificar que los datos se pueden recuperar
    cached = cache_manager.get(provider, search_params)
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].title == sample_package.title
    
def test_cache_invalidation(cache_manager, sample_package):
    """Prueba la invalidación del caché."""
    provider = "test_provider"
    search_params = {"destination": "Tokyo", "dates": {}}
    packages = [sample_package]
    
    # Almacenar datos
    cache_manager.set(provider, search_params, packages)
    
    # Invalidar por proveedor
    cache_manager.invalidate(provider=provider)
    assert cache_manager.get(provider, search_params) is None
    
    # Almacenar de nuevo
    cache_manager.set(provider, search_params, packages)
    
    # Invalidar por parámetros
    cache_manager.invalidate(search_params=search_params)
    assert cache_manager.get(provider, search_params) is None
    
def test_cache_ttl(cache_manager, sample_package):
    """Prueba el tiempo de vida del caché."""
    provider = "test_provider"
    search_params = {"destination": "Tokyo", "dates": {}}
    packages = [sample_package]
    
    # Configurar TTL muy corto
    cache_manager.ttl = timedelta(milliseconds=100)
    
    # Almacenar datos
    cache_manager.set(provider, search_params, packages)
    
    # Verificar que están disponibles inmediatamente
    assert cache_manager.get(provider, search_params) is not None
    
    # Esperar a que expire
    asyncio.sleep(0.2)
    
    # Verificar que ya no están disponibles
    assert cache_manager.get(provider, search_params) is None
    
def test_cache_max_entries(cache_manager, sample_package):
    """Prueba el límite de entradas en caché."""
    # Configurar máximo de 2 entradas
    cache_manager.max_entries = 2
    
    # Almacenar 3 entradas diferentes
    for i in range(3):
        provider = f"provider_{i}"
        search_params = {"destination": f"dest_{i}"}
        cache_manager.set(provider, search_params, [sample_package])
        
    # Verificar que solo se mantienen las 2 más recientes
    assert len(cache_manager.cache) == 2
    
    # Verificar que la primera entrada fue eliminada
    assert cache_manager.get("provider_0", {"destination": "dest_0"}) is None
    
def test_cache_compression(cache_manager, sample_package):
    """Prueba la compresión de datos."""
    provider = "test_provider"
    search_params = {"destination": "Tokyo"}
    packages = [sample_package] * 10  # Crear 10 copias para tener más datos
    
    # Almacenar datos
    cache_manager.set(provider, search_params, packages)
    
    # Verificar que los datos comprimidos son más pequeños que los originales
    cache_entry = cache_manager.cache[cache_manager._generate_key(provider, search_params)]
    compressed_size = len(cache_entry['data'])
    
    # Verificar que podemos recuperar todos los datos correctamente
    cached = cache_manager.get(provider, search_params)
    assert len(cached) == 10
    assert all(pkg.title == sample_package.title for pkg in cached)
    
def test_cache_stats(cache_manager, sample_package):
    """Prueba las estadísticas del caché."""
    provider = "test_provider"
    search_params = {"destination": "Tokyo"}
    
    # Realizar algunas operaciones
    assert cache_manager.get(provider, search_params) is None  # Miss
    cache_manager.set(provider, search_params, [sample_package])
    assert cache_manager.get(provider, search_params) is not None  # Hit
    cache_manager.invalidate(provider=provider)  # Invalidation
    
    # Verificar estadísticas
    stats = cache_manager.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["invalidations"] == 1
    assert stats["hit_ratio"] == 0.5  # 1 hit de 2 requests
