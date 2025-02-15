import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock
from ..core.analysis_engine import AnalysisEngine, AnalysisResult
from ..core.schemas import (
    TravelPackage, Accommodation, SalesQuery,
    SearchCriteria, Budget
)

@pytest.fixture
def mock_browser_manager():
    browser = Mock()
    browser.extract_list_data = AsyncMock()
    return browser

@pytest.fixture
def analysis_engine(mock_browser_manager):
    return AnalysisEngine(browser_manager=mock_browser_manager)

@pytest.fixture
def sample_packages():
    base_date = datetime.now()
    packages = []
    
    # Crear paquetes de muestra
    for i in range(10):
        package = TravelPackage(
            id=f"PKG{i}",
            title=f"Package {i}",
            description=f"Description {i}",
            destination="Cancun",
            price=Decimal(1000 + i * 200),
            currency="USD",
            duration=7 + i,
            start_date=base_date + timedelta(days=i*7),
            end_date=base_date + timedelta(days=(i+1)*7),
            provider="TestProvider",
            url=f"https://test.com/pkg{i}",
            accommodation=Accommodation(
                name=f"Hotel {i}",
                type="hotel",
                rating=4.0 + (i % 2),
                amenities=["wifi", "pool"],
                room_types=["standard", "suite"],
                location={"lat": 20.0, "lon": -87.0},
                images=[]
            ),
            activities=[
                "snorkel",
                "beach",
                "tour"
            ] if i % 2 == 0 else ["beach"],
            rating=4.0 + (i % 2),
            reviews_count=100 + i
        )
        packages.append(package)
    
    return packages

@pytest.fixture
def sample_query():
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
        },
        search_criteria=SearchCriteria(
            accommodation_type="hotel",
            meal_plan="all-inclusive",
            min_rating=4.0
        )
    )

@pytest.mark.asyncio
async def test_analyze_packages_basic(
    analysis_engine,
    sample_packages,
    sample_query
):
    """Test análisis básico de paquetes."""
    result = await analysis_engine.analyze_packages(
        sample_query,
        sample_packages
    )
    
    assert isinstance(result, AnalysisResult)
    assert len(result.packages) == len(sample_packages)
    assert "price_mean" in result.metrics
    assert "duration_mean" in result.metrics
    assert result.insights
    assert result.recommendations

@pytest.mark.asyncio
async def test_analyze_packages_empty(analysis_engine, sample_query):
    """Test análisis con lista vacía."""
    result = await analysis_engine.analyze_packages(
        sample_query,
        []
    )
    
    assert isinstance(result, AnalysisResult)
    assert len(result.packages) == 0
    assert result.insights["general"].startswith("Análisis limitado")

@pytest.mark.asyncio
async def test_segment_packages(
    analysis_engine,
    sample_packages
):
    """Test segmentación de paquetes."""
    segments = analysis_engine._segment_packages(sample_packages)
    
    assert isinstance(segments, dict)
    assert len(segments) > 0
    assert all(
        isinstance(pkgs, list)
        for pkgs in segments.values()
    )

def test_calculate_metrics(analysis_engine, sample_packages):
    """Test cálculo de métricas."""
    metrics = analysis_engine._calculate_metrics(sample_packages)
    
    assert "price_mean" in metrics
    assert "price_std" in metrics
    assert "duration_mean" in metrics
    assert metrics["sample_size"] == len(sample_packages)
    assert metrics["price_mean"] > 0
    assert metrics["duration_mean"] > 0

@pytest.mark.asyncio
async def test_generate_recommendations(
    analysis_engine,
    sample_packages,
    sample_query
):
    """Test generación de recomendaciones."""
    recommendations = analysis_engine._generate_recommendations(
        sample_query,
        sample_packages,
        {"standard": sample_packages[:3]}
    )
    
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0
    assert all(
        isinstance(p, TravelPackage)
        for p in recommendations
    )
    
    # Verificar filtros
    assert all(
        p.price <= sample_query.preferences["max_budget"]
        for p in recommendations
    )
    assert all(
        p.duration >= sample_query.preferences["min_nights"]
        for p in recommendations
    )

@pytest.mark.asyncio
async def test_analyze_price_trends(
    analysis_engine,
    sample_packages,
    mock_browser_manager
):
    """Test análisis de tendencias de precios."""
    # Configurar mock
    mock_browser_manager.extract_list_data.return_value = [
        {"date": "2025-01-01", "price": "$1000"},
        {"date": "2025-01-02", "price": "$1100"}
    ]
    
    trends = await analysis_engine._analyze_price_trends(
        sample_packages[:2]
    )
    
    assert isinstance(trends, dict)
    assert len(trends) > 0
    assert all(
        isinstance(prices, list)
        for prices in trends.values()
    )
    assert mock_browser_manager.extract_list_data.called

@pytest.mark.asyncio
async def test_process_feedback(analysis_engine, sample_packages):
    """Test procesamiento de feedback."""
    analysis = AnalysisResult(
        packages=sample_packages,
        metrics={
            "price_mean": 1500,
            "duration_mean": 7
        },
        segments={},
        recommendations=sample_packages[:3],
        insights={},
        price_trends={}
    )
    
    feedback = {
        "precio": "muy alto",
        "duracion": "muy corta",
        "actividades": ["snorkel", "diving"]
    }
    
    refinements = analysis_engine._process_feedback(
        feedback,
        analysis
    )
    
    assert isinstance(refinements, dict)
    assert "max_budget" in refinements
    assert "min_nights" in refinements
    assert "activities" in refinements
    assert refinements["max_budget"] < 1500
    assert refinements["min_nights"] > 7
