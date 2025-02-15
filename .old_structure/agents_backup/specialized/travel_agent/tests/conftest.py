"""Fixtures for testing."""

import pytest
from datetime import datetime
from typing import Generator
from pydantic import HttpUrl
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from ..providers import TourismProvider, ExtractionRules

@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Fixture para proveer un navegador para las pruebas."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()

@pytest.fixture
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Fixture para proveer un contexto de navegador."""
    context = browser.new_context()
    yield context
    context.close()

@pytest.fixture
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Fixture para proveer una página de navegador."""
    page = context.new_page()
    yield page
    page.close()

@pytest.fixture
def mock_tourism_provider():
    """Fixture para proveer un mock de TourismProvider."""
    class MockTourismProvider(TourismProvider):
        async def search_packages(self, destination, start_date, end_date, **kwargs):
            """Mock de búsqueda de paquetes."""
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
                
            return [{
                "id": "test-package-1",
                "provider": self.name,
                "destination": destination,
                "title": "Test Package",
                "description": "A test package",
                "price": 1000.0,
                "currency": "USD",
                "duration": 10,
                "dates": {
                    "start": start_date,
                    "end": end_date
                },
                "accommodation": {
                    "name": "Test Hotel",
                    "type": "hotel",
                    "location": destination,
                    "rating": 4.5,
                    "amenities": ["wifi", "pool"],
                    "room_types": ["single", "double"]
                },
                "activities": [{
                    "name": "City Tour",
                    "description": "Tour por la ciudad",
                    "duration": "4 hours",
                    "price": 50.0,
                    "included": ["guide", "transport"],
                    "requirements": ["comfortable shoes"]
                }],
                "included_services": ["breakfast", "airport transfer"],
                "excluded_services": ["lunch", "dinner"],
                "booking_url": "https://example.com/booking",
                "terms_conditions": "Standard terms apply"
            }]
            
    return MockTourismProvider(
        name="MockProvider",
        base_url=HttpUrl("https://mock-provider.com"),
        supported_destinations=["Bariloche", "Mar del Plata"],
        last_updated=datetime.now(),
        extraction_rules=ExtractionRules()
    )
