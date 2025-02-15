"""Tests for tourism providers."""

import pytest
from datetime import datetime
from pydantic import HttpUrl
from ..providers import TourismProvider, ExtractionRules
from ..schemas import TravelPackage, Accommodation, Activity

@pytest.mark.asyncio
async def test_tourism_provider_base_class():
    """Prueba la clase base TourismProvider."""
    provider = TourismProvider(
        name="TestProvider",
        base_url=HttpUrl("https://test.com"),
        supported_destinations=["Bariloche", "Mar del Plata"],
        last_updated=datetime.now(),
        extraction_rules=ExtractionRules()
    )
    
    assert provider.name == "TestProvider"
    assert str(provider.base_url) == "https://test.com/"
    assert "Bariloche" in provider.supported_destinations

@pytest.mark.asyncio
async def test_aero_provider(mock_tourism_provider):
    """Prueba el proveedor Aero."""
    provider = mock_tourism_provider
    
    # Prueba búsqueda de paquetes
    packages = await provider.search_packages(
        destination="Bariloche",
        start_date="2025-03-01",
        end_date="2025-03-10"
    )
    
    assert len(packages) > 0
    package = packages[0]
    
    # Verificar que el paquete es una instancia válida
    assert isinstance(package, dict)
    
    # Crear un TravelPackage válido
    travel_package = TravelPackage(
        id="test-package-1",
        provider=provider.name,
        destination=package["destination"],
        title=package["title"],
        description=package["description"],
        price=package["price"],
        currency=package["currency"],
        duration=package["duration"],
        start_date=datetime.strptime(package["dates"]["start"], "%Y-%m-%d"),
        end_date=datetime.strptime(package["dates"]["end"], "%Y-%m-%d"),
        accommodation=Accommodation(
            name=package["accommodation"]["name"],
            type=package["accommodation"]["type"],
            location=package["accommodation"]["location"],
            rating=package["accommodation"]["rating"],
            amenities=package["accommodation"]["amenities"],
            room_types=package["accommodation"]["room_types"]
        ),
        activities=[
            Activity(
                name=activity["name"],
                description=activity["description"],
                duration=activity["duration"],
                price=activity["price"],
                included=activity["included"],
                requirements=activity["requirements"]
            ) for activity in package["activities"]
        ],
        included_services=package["included_services"],
        excluded_services=package["excluded_services"],
        booking_url=package["booking_url"],
        terms_conditions=package["terms_conditions"]
    )
    
    assert travel_package.id == "test-package-1"
    assert travel_package.provider == provider.name
    assert travel_package.destination == "Bariloche"

@pytest.mark.asyncio
async def test_package_validation(mock_tourism_provider):
    """Prueba la validación de paquetes."""
    provider = mock_tourism_provider
    
    # Crear un paquete válido
    valid_package = {
        "id": "test-package-2",
        "provider": provider.name,
        "destination": "Bariloche",
        "title": "Test Package",
        "description": "A test package",
        "price": 1000.0,
        "currency": "USD",
        "duration": 7,
        "start_date": datetime.strptime("2025-03-01", "%Y-%m-%d"),
        "end_date": datetime.strptime("2025-03-10", "%Y-%m-%d"),
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
        "excluded_services": ["dinner"],
        "booking_url": "https://example.com/booking",
        "terms_conditions": "Standard terms apply"
    }
    
    # Verificar que el paquete válido pasa la validación
    assert await provider.validate_package(valid_package)
    
    # Crear un paquete inválido (sin precio)
    invalid_package = valid_package.copy()
    del invalid_package["price"]
    
    # Verificar que el paquete inválido falla la validación
    with pytest.raises(ValueError):
        await provider.validate_package(invalid_package)

@pytest.mark.asyncio
async def test_date_validation(mock_tourism_provider):
    """Prueba la validación de fechas en los paquetes."""
    provider = mock_tourism_provider
    
    # Prueba con fechas válidas
    packages = await provider.search_packages(
        destination="Bariloche",
        start_date="2025-03-01",
        end_date="2025-03-10"
    )
    
    assert len(packages) > 0
    
    # Prueba con fechas inválidas
    with pytest.raises(ValueError):
        await provider.search_packages(
            destination="Bariloche",
            start_date="invalid-date",
            end_date="2025-03-10"
        )
