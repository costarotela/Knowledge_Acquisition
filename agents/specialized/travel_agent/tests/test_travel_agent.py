"""Pruebas para el agente de viajes."""
import pytest
import pytest_asyncio
from datetime import datetime
from ..travel_agent import TravelAgent
from ..schemas import TravelPackage, Activity, Accommodation
from .mocks.knowledge_base import MockKnowledgeBase
from ..providers import TourismProvider, ExtractionRules
from pydantic import HttpUrl

@pytest.fixture
def travel_agent():
    """Fixture para proveer una instancia del agente de viajes."""
    knowledge_base = MockKnowledgeBase()
    return TravelAgent(
        knowledge_base=knowledge_base,
        providers=[]
    )

@pytest.fixture
def sample_packages():
    """Fixture para proveer paquetes de ejemplo."""
    return [
        TravelPackage(
            id="package-1",
            provider="Provider1",
            destination="Bariloche",
            title="Economic Package",
            description="Basic package with essential services",
            price=800.0,
            currency="USD",
            duration=7,
            start_date=datetime(2025, 3, 1),
            end_date=datetime(2025, 3, 7),
            accommodation=Accommodation(
                name="Basic Hotel",
                type="hotel",
                location="Downtown",
                rating=3.5,
                amenities=["wifi"],
                room_types=["double"]
            ),
            activities=[
                Activity(
                    name="City Tour",
                    description="Basic city tour",
                    duration="3 hours",
                    price=30.0,
                    included=["guide"],
                    requirements=[]
                )
            ],
            included_services=["breakfast"],
            excluded_services=["lunch", "dinner"],
            booking_url="https://example.com/package1",
            terms_conditions="Basic terms"
        ),
        TravelPackage(
            id="package-2",
            provider="Provider2",
            destination="Bariloche",
            title="Premium Package",
            description="Luxury all-inclusive package",
            price=1500.0,
            currency="USD",
            duration=7,
            start_date=datetime(2025, 3, 1),
            end_date=datetime(2025, 3, 7),
            accommodation=Accommodation(
                name="Luxury Resort",
                type="resort",
                location="Lakeside",
                rating=5.0,
                amenities=["wifi", "pool", "spa", "gym"],
                room_types=["suite", "double deluxe"]
            ),
            activities=[
                Activity(
                    name="Premium City Tour",
                    description="VIP city tour with lunch",
                    duration="6 hours",
                    price=100.0,
                    included=["guide", "lunch", "transport"],
                    requirements=[]
                ),
                Activity(
                    name="Lake Excursion",
                    description="Private boat tour",
                    duration="4 hours",
                    price=150.0,
                    included=["guide", "equipment"],
                    requirements=["swimming ability"]
                )
            ],
            included_services=["all meals", "airport transfer", "welcome drink"],
            excluded_services=["premium drinks"],
            booking_url="https://example.com/package2",
            terms_conditions="Premium terms"
        )
    ]

@pytest_asyncio.fixture
async def travel_agent_initialized():
    """Fixture para proveer un agente de viajes con un proveedor inicializado."""
    agent = TravelAgent(knowledge_base=MockKnowledgeBase())
    
    # Agregar un proveedor de prueba
    provider = TourismProvider(
        name="TestProvider",
        base_url=HttpUrl("https://test-provider.com"),
        supported_destinations=["Bariloche", "Mar del Plata"],
        last_updated=datetime.now(),
        extraction_rules=ExtractionRules()
    )
    agent.providers.append(provider)
    
    return agent

@pytest.mark.asyncio
async def test_search_packages(travel_agent_initialized):
    """Prueba la búsqueda de paquetes."""
    packages = await travel_agent_initialized.search_packages(
        destination="Bariloche",
        dates={
            "start": "2025-03-01",
            "end": "2025-03-10"
        }
    )
    
    assert len(packages) > 0
    package = packages[0]
    
    # Verificar que es una instancia válida de TravelPackage
    assert isinstance(package, TravelPackage)
    assert package.destination == "Bariloche"
    assert isinstance(package.price, float)
    assert package.duration > 0

@pytest.mark.asyncio
async def test_compare_packages(travel_agent, sample_packages):
    """Prueba la comparación de paquetes."""
    analysis = await travel_agent.compare_packages(sample_packages)
    
    # Verificar estructura del análisis
    assert "price_analysis" in analysis
    assert "features_comparison" in analysis
    assert "value_ranking" in analysis
    assert "recommendations" in analysis
    
    # Verificar análisis de precios
    price_analysis = analysis["price_analysis"]
    assert price_analysis["min_price"] == 800.0
    assert price_analysis["max_price"] == 1500.0
    assert price_analysis["avg_price"] == 1150.0
    
    # Verificar ranking de valor
    value_ranking = analysis["value_ranking"]
    assert len(value_ranking) == 2
    assert all("value_score" in item for item in value_ranking)
    
    # Verificar recomendaciones
    recommendations = analysis["recommendations"]
    assert len(recommendations) > 0
    assert all("category" in item for item in recommendations)
    assert all("package_id" in item for item in recommendations)
    assert all("reason" in item for item in recommendations)

@pytest.mark.asyncio
async def test_analyze_provider(travel_agent):
    """Prueba el análisis de un nuevo proveedor."""
    provider_url = "https://example-provider.com"
    
    provider = await travel_agent.analyze_provider(provider_url)
    
    # Verificar que se creó un proveedor válido
    assert provider is not None
    assert hasattr(provider, 'name')
    assert hasattr(provider, 'base_url')
    assert hasattr(provider, 'search_packages')
    assert hasattr(provider, 'validate_package')
