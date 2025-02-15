"""Configuración de tests."""

import pytest
from unittest.mock import Mock, AsyncMock
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from agents.specialized.travel_agent.core.browser_manager import BrowserManager
from agents.specialized.travel_agent.core.analysis_engine import AnalysisEngine
from agents.specialized.travel_agent.core.sales_assistant import SalesAssistant
from agents.specialized.travel_agent.core.schemas import (
    TravelPackage, SalesQuery, Budget, SalesReport,
    AnalysisResult, SessionState, ProviderConfig
)

@pytest.fixture
def mock_browser():
    """Mock del navegador."""
    browser = Mock()
    browser.get = AsyncMock()
    browser.find_elements = AsyncMock()
    browser.execute_script = AsyncMock()
    return browser

@pytest.fixture
def browser_manager(mock_browser):
    """Fixture para BrowserManager."""
    return BrowserManager(browser=mock_browser)

@pytest.fixture
def analysis_engine(mock_browser):
    """Fixture para AnalysisEngine."""
    return AnalysisEngine(browser_manager=mock_browser)

@pytest.fixture
def sales_assistant(mock_browser):
    """Fixture para SalesAssistant."""
    return SalesAssistant(browser_manager=mock_browser)

@pytest.fixture
def sample_package():
    """Paquete de ejemplo para tests."""
    return TravelPackage(
        id="PKG1",
        title="Test Package",
        description="Test Description",
        destination="Cancun",
        price=1500.00,
        currency="USD",
        duration=7,
        start_date="2025-03-01",
        end_date="2025-03-08",
        provider="TestProvider",
        url="https://test.com/pkg1",
        accommodation=Mock(),
        activities=["snorkel", "beach"],
        rating=4.5
    )

@pytest.fixture
def sample_query():
    """Query de ejemplo para tests."""
    return SalesQuery(
        client_name="Test Client",
        destination="Cancun",
        dates={
            "departure": "2025-03-01",
            "return": "2025-03-08"
        },
        preferences={
            "max_budget": 2000,
            "min_nights": 5,
            "activities": ["snorkel", "beach"]
        }
    )

@pytest.fixture
def sample_analysis(sample_package):
    """Análisis de ejemplo para tests."""
    return AnalysisResult(
        packages=[sample_package],
        metrics={
            "price_mean": 1500,
            "price_std": 200,
            "duration_mean": 7
        },
        segments={
            "standard": [sample_package]
        },
        recommendations=[sample_package],
        insights={
            "valor": "Buen valor por el precio",
            "temporada": "Temporada alta"
        },
        price_trends={}
    )

@pytest.fixture
def sample_provider_config():
    """Configuración de proveedor para tests."""
    return ProviderConfig(
        name="test_provider",
        type="travel",
        base_url="https://test.com",
        requires_auth=False,
        selectors={
            "package_list": ".package-item",
            "price": ".price",
            "title": ".title"
        },
        data_patterns={
            "price": r"\$(\d+)",
            "date": r"(\d{4}-\d{2}-\d{2})"
        },
        extraction={
            "list_mode": "pagination",
            "max_items": 100,
            "delay": 1
        }
    )
