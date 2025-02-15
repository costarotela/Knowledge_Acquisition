import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import json

from ..core.sales_assistant import SalesAssistant
from ..core.schemas import (
    TravelPackage, SalesQuery, Budget, SalesReport,
    AnalysisResult, SessionState
)

@pytest.fixture
def mock_travel_agent():
    agent = Mock()
    agent.search_packages = AsyncMock()
    agent.browser_manager = Mock()
    return agent

@pytest.fixture
def mock_analysis_engine():
    engine = Mock()
    engine.analyze_packages = AsyncMock()
    return engine

@pytest.fixture
def sales_assistant(mock_travel_agent, tmp_path):
    # Crear directorio temporal para templates
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    
    # Crear template de prueba
    template_file = templates_dir / "default.json"
    template_file.write_text(json.dumps({
        "sections": ["header", "packages", "analysis"],
        "styles": {"theme": "default"}
    }))
    
    assistant = SalesAssistant(
        agent=mock_travel_agent,
        templates_dir=templates_dir
    )
    assistant.analysis_engine = mock_analysis_engine()
    return assistant

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
        }
    )

@pytest.fixture
def sample_package():
    return TravelPackage(
        id="PKG1",
        title="Test Package",
        description="Test Description",
        destination="Cancun",
        price=Decimal("1500.00"),
        currency="USD",
        duration=7,
        start_date=datetime.now(),
        end_date=datetime.now(),
        provider="TestProvider",
        url="https://test.com/pkg1",
        accommodation=Mock(),
        activities=["snorkel", "beach"],
        rating=4.5
    )

@pytest.fixture
def sample_analysis(sample_package):
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

@pytest.mark.asyncio
async def test_start_interaction(
    sales_assistant,
    sample_query,
    sample_package,
    sample_analysis,
    mock_travel_agent
):
    """Test inicio de interacción."""
    # Configurar mocks
    mock_travel_agent.search_packages.return_value = [sample_package]
    sales_assistant.analysis_engine.analyze_packages.return_value = sample_analysis
    
    result = await sales_assistant.start_interaction(sample_query)
    
    assert result["status"] == "success"
    assert "session_id" in result
    assert "budget" in result
    assert "insights" in result
    assert mock_travel_agent.search_packages.called
    assert sales_assistant.analysis_engine.analyze_packages.called

@pytest.mark.asyncio
async def test_start_interaction_no_packages(
    sales_assistant,
    sample_query,
    mock_travel_agent
):
    """Test inicio sin paquetes encontrados."""
    mock_travel_agent.search_packages.return_value = []
    
    result = await sales_assistant.start_interaction(sample_query)
    
    assert result["status"] == "error"
    assert "No se encontraron paquetes" in result["message"]

@pytest.mark.asyncio
async def test_refine_search(
    sales_assistant,
    sample_query,
    sample_package,
    sample_analysis
):
    """Test refinamiento de búsqueda."""
    # Crear sesión inicial
    session_id = "test_session"
    sales_assistant.session_manager.create_session(sample_query)
    sales_assistant.session_manager.update_session(
        session_id,
        {
            "query": sample_query,
            "current_analysis": sample_analysis,
            "current_budget": Mock(),
            "interaction_count": 1
        }
    )
    
    # Configurar mocks para refinamiento
    mock_travel_agent.search_packages.return_value = [sample_package]
    sales_assistant.analysis_engine.analyze_packages.return_value = sample_analysis
    
    result = await sales_assistant.refine_search(
        session_id,
        feedback={"precio": "muy alto"},
        parameter_updates={"max_budget": 1800}
    )
    
    assert result["status"] == "success"
    assert "budget" in result
    assert "insights" in result
    assert "changes" in result

def test_process_feedback(
    sales_assistant,
    sample_analysis
):
    """Test procesamiento de feedback."""
    feedback = {
        "precio": "muy alto",
        "duracion": "muy corta",
        "actividades": ["diving"]
    }
    
    refinements = sales_assistant._process_feedback(
        feedback,
        sample_analysis
    )
    
    assert isinstance(refinements, dict)
    assert "max_budget" in refinements
    assert "min_nights" in refinements
    assert "activities" in refinements

def test_generate_budget(
    sales_assistant,
    sample_query,
    sample_analysis
):
    """Test generación de presupuesto."""
    budget = sales_assistant._generate_budget(
        sample_query,
        sample_analysis,
        is_refined=False
    )
    
    assert isinstance(budget, Budget)
    assert budget.client_name == sample_query.client_name
    assert budget.destination == sample_query.destination
    assert budget.recommended_package
    assert budget.price_analysis
    assert budget.value_insights
    assert budget.seasonal_info

def test_end_interaction(
    sales_assistant,
    sample_query,
    sample_analysis
):
    """Test finalización de interacción."""
    # Crear sesión de prueba
    session_id = "test_session"
    budget = Mock()
    
    sales_assistant.session_manager.create_session(sample_query)
    sales_assistant.session_manager.update_session(
        session_id,
        {
            "query": sample_query,
            "current_analysis": sample_analysis,
            "current_budget": budget,
            "interaction_count": 2
        }
    )
    
    report = sales_assistant.end_interaction(
        session_id,
        reason="presupuesto_aceptado"
    )
    
    assert isinstance(report, SalesReport)
    assert report.query == sample_query
    assert report.final_budget == budget
    assert report.interaction_count == 2
    assert report.end_reason == "presupuesto_aceptado"
    assert report.insights == sample_analysis.insights
    assert report.metrics == sample_analysis.metrics

def test_summarize_changes(
    sales_assistant,
    sample_package,
    sample_analysis
):
    """Test resumen de cambios."""
    # Crear análisis previo
    previous_analysis = AnalysisResult(
        packages=[sample_package],
        metrics={
            "price_mean": 2000,
            "price_std": 300,
            "duration_mean": 7
        },
        segments={
            "standard": [sample_package] * 2
        },
        recommendations=[sample_package],
        insights={},
        price_trends={}
    )
    
    changes = sales_assistant._summarize_changes(
        previous_analysis,
        sample_analysis
    )
    
    assert isinstance(changes, dict)
    assert "precio_medio" in changes
    assert "segment_standard" in changes
    assert changes["precio_medio"]["variacion"]
