import pytest
from unittest.mock import Mock, patch
from agents.specialized.rag_agent import RAGAgent
from core_system.knowledge_base import UnifiedKnowledgeStore

@pytest.fixture
def mock_knowledge_store():
    return Mock(spec=UnifiedKnowledgeStore)

@pytest.fixture
def rag_agent(mock_knowledge_store):
    return RAGAgent(knowledge_store=mock_knowledge_store)

def test_knowledge_retrieval():
    """Test knowledge retrieval and reasoning"""
    agent = RAGAgent()
    query = "What is the relationship between exercise and mitochondria?"
    
    # Mock knowledge store to return relevant results
    mock_results = [
        {
            "text": "Exercise increases mitochondrial function",
            "score": 0.95,
            "metadata": {"source": "scientific_paper"}
        }
    ]
    agent.knowledge_store.query_knowledge.return_value = mock_results
    
    response = agent.process_query(query)
    
    assert response["answer"] is not None
    assert response["sources"] is not None
    assert response["confidence"] > 0.8

def test_hypothesis_generation():
    """Test generation of hypotheses from retrieved knowledge"""
    agent = RAGAgent()
    
    knowledge = [
        {
            "text": "Regular exercise improves mitochondrial function",
            "score": 0.9
        },
        {
            "text": "Mitochondria are key for energy production",
            "score": 0.85
        }
    ]
    
    hypotheses = agent.generate_hypotheses(knowledge)
    
    assert len(hypotheses) > 0
    for hypothesis in hypotheses:
        assert "statement" in hypothesis
        assert "confidence" in hypothesis
        assert "supporting_evidence" in hypothesis

def test_source_validation():
    """Test validation of knowledge sources"""
    agent = RAGAgent()
    
    invalid_source = {
        "text": "Unverified claim",
        "metadata": {"source": "unknown"}
    }
    
    with pytest.raises(ValueError):
        agent.validate_source(invalid_source)

def test_confidence_threshold():
    """Test confidence threshold filtering"""
    agent = RAGAgent(confidence_threshold=0.8)
    
    knowledge = [
        {"text": "High confidence fact", "score": 0.9},
        {"text": "Low confidence fact", "score": 0.7}
    ]
    
    filtered = agent.filter_by_confidence(knowledge)
    
    assert len(filtered) == 1
    assert filtered[0]["score"] >= 0.8
