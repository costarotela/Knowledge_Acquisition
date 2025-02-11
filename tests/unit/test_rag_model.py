"""Tests básicos para el modelo RAG."""
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from langchain.schema import AIMessage
from src.agent.models.rag_model import AgenticNutritionRAG
from src.agent.core.base import AgentContext

# Datos de prueba básicos
TEST_QUERY = "¿Cuál es la mejor dieta para bajar de peso?"
TEST_CONTEXT = "La mejor dieta es aquella que se puede mantener a largo plazo."
TEST_RESPONSE = "La mejor dieta para bajar de peso es aquella que se adapta a tus necesidades individuales"

@pytest.fixture
def mock_openai():
    with patch('langchain.chat_models.ChatOpenAI') as mock:
        mock_chat = AsyncMock()
        mock_chat.agenerate.return_value.generations = [[AIMessage(content=TEST_RESPONSE)]]
        mock.return_value = mock_chat
        yield mock

@pytest.fixture
def mock_supabase():
    with patch('supabase.create_client') as mock:
        mock_db = MagicMock()
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value.data = [{'content': TEST_CONTEXT}]
        mock_db.rpc.return_value = mock_rpc
        mock.return_value = mock_db
        yield mock

@pytest_asyncio.fixture
async def rag_model(mock_openai, mock_supabase):
    model = AgenticNutritionRAG()
    model.train = AsyncMock()
    await model.initialize()
    yield model
    await model.shutdown()

@pytest.mark.asyncio
async def test_predict_basic_flow(rag_model):
    """Test del flujo básico de predicción."""
    agent_context = AgentContext(session_id="test_session")
    result = await rag_model.predict(TEST_QUERY, agent_context)
    
    assert isinstance(result, dict)
    assert "response" in result
    # Verificar que la respuesta contiene palabras clave esperadas
    assert any(word in result["response"].lower() for word in ["dieta", "peso", "necesidades"])

@pytest.mark.asyncio
async def test_error_handling(rag_model):
    """Test básico de manejo de errores."""
    # Simular error en get_context
    with patch.object(rag_model, 'get_context', side_effect=Exception("API Error")):
        agent_context = AgentContext(session_id="test_session")
        result = await rag_model.predict("test query", agent_context)
        
        assert isinstance(result, dict)
        assert "error" in result["metadata"]
        assert "API Error" in result["metadata"]["error"]
