"""
Unit tests for RAG Agent.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from agents.specialized.rag_agent.rag_agent import RAGAgent
from agents.specialized.rag_agent.schemas import (
    QueryType, ReasoningStep, CitationInfo,
    QueryContext, ReasoningChain, KnowledgeFragment,
    GeneratedResponse, AgentAction, AgentState
)
from core_system.agent_orchestrator.base import Task, TaskResult

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "model_name": "gpt-4",
        "max_documents": 5,
        "vector_store_path": "/tmp/test_vector_store"
    }

@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    return Mock()

@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    return Mock()

@pytest.fixture
async def rag_agent(mock_config, mock_llm, mock_vector_store):
    """Create RAG agent for testing."""
    with patch("langchain.chat_models.ChatOpenAI") as mock_chat:
        mock_chat.return_value = mock_llm
        with patch("langchain.vectorstores.Chroma") as mock_chroma:
            mock_chroma.return_value = mock_vector_store
            agent = RAGAgent(config=mock_config)
            await agent.initialize()
            yield agent
            await agent.cleanup()

@pytest.mark.asyncio
async def test_process_extraction(rag_agent, mock_llm):
    """Test knowledge extraction processing."""
    # Setup mock responses
    mock_llm.arun.side_effect = [
        {
            "description": "Test reasoning",
            "confidence": 0.8,
            "conclusion": "Test conclusion"
        },
        {
            "response": "Test response",
            "generated_knowledge": {
                "type": "test",
                "content": "test content",
                "confidence": 0.9
            }
        }
    ]
    
    # Create test task
    task = Task(
        id="test_task",
        task_type="extraction",
        input_data={
            "query": "test query",
            "query_type": QueryType.FACTUAL,
            "depth": 1
        }
    )
    
    # Execute task
    result = await rag_agent._process_extraction(task)
    
    # Verify results
    assert result.success
    assert "response" in result.data
    assert result.metrics["reasoning_steps"] == 1
    assert result.metrics["citations_used"] >= 0

@pytest.mark.asyncio
async def test_execute_reasoning(rag_agent, mock_vector_store):
    """Test reasoning chain execution."""
    # Setup mock documents
    mock_docs = [
        KnowledgeFragment(
            id="test_1",
            content="test content 1",
            metadata={"type": "test"},
            confidence=0.8
        ),
        KnowledgeFragment(
            id="test_2",
            content="test content 2",
            metadata={"type": "test"},
            confidence=0.9
        )
    ]
    mock_vector_store.as_retriever().aget_relevant_documents.return_value = mock_docs
    
    # Create test query and context
    query = "test query"
    context = QueryContext(
        query_type=QueryType.FACTUAL,
        required_depth=1
    )
    
    # Execute reasoning
    chain = await rag_agent._execute_reasoning(query, context)
    
    # Verify chain
    assert chain is not None
    assert len(chain.steps) > 0
    assert chain.confidence_score > 0
    assert chain.execution_time > 0

@pytest.mark.asyncio
async def test_retrieve_relevant_documents(rag_agent, mock_vector_store):
    """Test document retrieval."""
    # Setup test query and context
    query = "test query"
    context = QueryContext(
        query_type=QueryType.FACTUAL,
        required_depth=1
    )
    
    # Execute retrieval
    docs = await rag_agent._retrieve_relevant_documents(query, context)
    
    # Verify results
    assert len(docs) > 0
    for doc in docs:
        assert isinstance(doc, KnowledgeFragment)
        assert doc.content is not None
        assert doc.confidence > 0

@pytest.mark.asyncio
async def test_execute_reasoning_step(rag_agent, mock_llm):
    """Test single reasoning step execution."""
    # Setup test data
    query = "test query"
    docs = [
        KnowledgeFragment(
            id="test_1",
            content="test content",
            metadata={"type": "test"},
            confidence=0.8
        )
    ]
    context = QueryContext(
        query_type=QueryType.FACTUAL,
        required_depth=1
    )
    
    # Execute step
    step = await rag_agent._execute_reasoning_step(
        query=query,
        previous_conclusion=None,
        documents=docs,
        step_number=1,
        context=context
    )
    
    # Verify step
    assert step is not None
    assert step.step_number == 1
    assert step.confidence > 0
    assert len(step.evidence) > 0

@pytest.mark.asyncio
async def test_generate_response(rag_agent, mock_llm):
    """Test response generation."""
    # Setup test data
    query = "test query"
    reasoning = ReasoningChain(
        query=query,
        context=QueryContext(
            query_type=QueryType.FACTUAL,
            required_depth=1
        ),
        steps=[
            ReasoningStep(
                step_number=1,
                description="test step",
                evidence=[{
                    "source_id": "test",
                    "source_type": "test",
                    "content": "test content",
                    "relevance": 0.8
                }],
                confidence=0.8,
                intermediate_conclusion="test conclusion"
            )
        ],
        citations=[
            CitationInfo(
                source_id="test",
                source_type="test",
                content_snippet="test content",
                relevance_score=0.8
            )
        ],
        final_conclusion="test conclusion",
        confidence_score=0.8,
        execution_time=1.0
    )
    
    # Execute generation
    response = await rag_agent._generate_response(
        query=query,
        reasoning=reasoning,
        context=reasoning.context
    )
    
    # Verify response
    assert response is not None
    assert response.response_text is not None
    assert len(response.supporting_fragments) > 0
    assert response.reasoning_chain == reasoning
