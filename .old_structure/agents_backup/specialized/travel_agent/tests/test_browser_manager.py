"""Tests for browser manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from ..browser_manager import BrowserManager
from ..tests.mocks.browser_use import BrowserAgent

@pytest.mark.asyncio
async def test_browser_manager_initialization():
    """Prueba la inicialización del BrowserManager."""
    manager = BrowserManager()
    assert manager is not None
    assert hasattr(manager, 'extract_data')
    assert isinstance(manager.browser, BrowserAgent)

@pytest.mark.asyncio
async def test_browser_manager_navigation():
    """Prueba la navegación básica."""
    manager = BrowserManager()
    url = "https://example.com"
    
    # Mock del método navigate
    manager.browser.navigate = AsyncMock()
    
    await manager.navigate(url)
    manager.browser.navigate.assert_awaited_once_with(url)

@pytest.mark.asyncio
async def test_data_extraction():
    """Prueba la extracción de datos."""
    manager = BrowserManager()
    rules = {
        "title": ".package-title",
        "price": ".package-price",
        "description": ".package-description"
    }
    
    # Mock del método extract_data
    expected_data = {
        "title": "Test Package",
        "price": 1000.0,
        "description": "A test package",
        "dates": {
            "start": "2025-03-01",
            "end": "2025-03-10"
        },
        "accommodation": {
            "name": "Test Hotel",
            "type": "hotel",
            "location": "Bariloche",
            "rating": 4.0,
            "amenities": ["wifi"],
            "room_types": ["double"]
        },
        "activities": [{
            "name": "Hiking",
            "description": "Mountain hiking",
            "duration": "6 hours",
            "price": 80.0,
            "included": ["guide"],
            "requirements": ["good condition"]
        }],
        "included_services": ["breakfast"],
        "excluded_services": ["dinner"]
    }
    manager.browser.extract_data = AsyncMock(return_value=expected_data)
    
    data = await manager.extract_data(rules)
    assert data == expected_data
    manager.browser.extract_data.assert_awaited_once_with(rules)

@pytest.mark.asyncio
async def test_error_handling():
    """Prueba el manejo de errores durante la extracción."""
    manager = BrowserManager()
    rules = {"invalid": "rules"}
    
    # Mock del método extract_data para lanzar una excepción
    manager.browser.extract_data = AsyncMock(side_effect=Exception("Test error"))
    
    data = await manager.extract_data(rules)
    assert data == {}
