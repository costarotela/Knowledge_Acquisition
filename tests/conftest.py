"""
Configuración de pytest para los tests.
"""
import pytest
import asyncio

# Configurar el scope del event loop para fixtures asíncronos
@pytest.fixture(scope="session")
def event_loop():
    """Crear un event loop para toda la sesión de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Configurar el modo estricto para asyncio
def pytest_configure(config):
    """Configurar pytest."""
    config.option.asyncio_mode = "strict"
