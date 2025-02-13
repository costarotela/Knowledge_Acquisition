import pytest
from unittest.mock import Mock, patch
from core_system.knowledge_base.unified_store import UnifiedKnowledgeStore
from core_system.knowledge_base.vector_db import VectorStore
from core_system.knowledge_base.graph_db import GraphStore

@pytest.fixture
def mock_vector_store():
    return Mock(spec=VectorStore)

@pytest.fixture
def mock_graph_store():
    return Mock(spec=GraphStore)

@pytest.fixture
def knowledge_store(mock_vector_store, mock_graph_store):
    return UnifiedKnowledgeStore(
        vector_store=mock_vector_store,
        graph_store=mock_graph_store
    )

def test_store_knowledge():
    """Test storing knowledge in both vector and graph stores"""
    store = UnifiedKnowledgeStore()
    
    knowledge = {
        "text": "Test knowledge",
        "metadata": {"source": "test", "type": "text"},
        "relationships": [
            {"from": "concept1", "to": "concept2", "type": "related"}
        ]
    }
    
    store.store_knowledge(knowledge)
    
    # Verify knowledge was stored in both stores
    assert store.vector_store.store.called
    assert store.graph_store.add_relationships.called

def test_query_knowledge():
    """Test querying knowledge from both stores"""
    store = UnifiedKnowledgeStore()
    query = "test query"
    
    # Mock vector store to return some results
    mock_vector_results = [
        {"text": "result1", "score": 0.9},
        {"text": "result2", "score": 0.8}
    ]
    store.vector_store.query.return_value = mock_vector_results
    
    # Mock graph store to return related concepts
    mock_graph_results = [
        {"concept": "related1", "relationship": "type1"},
        {"concept": "related2", "relationship": "type2"}
    ]
    store.graph_store.get_related_concepts.return_value = mock_graph_results
    
    results = store.query_knowledge(query)
    
    assert len(results["vector_results"]) == 2
    assert len(results["graph_results"]) == 2

def test_knowledge_validation():
    """Test knowledge validation before storing"""
    store = UnifiedKnowledgeStore()
    
    invalid_knowledge = {
        "text": "",  # Empty text should be invalid
        "metadata": {}
    }
    
    with pytest.raises(ValueError):
        store.store_knowledge(invalid_knowledge)

def test_knowledge_deduplication():
    """Test that duplicate knowledge is handled properly"""
    store = UnifiedKnowledgeStore()
    
    knowledge = {
        "text": "Test knowledge",
        "metadata": {"source": "test"}
    }
    
    # Store same knowledge twice
    store.store_knowledge(knowledge)
    store.store_knowledge(knowledge)
    
    # Verify knowledge was only stored once
    assert store.vector_store.store.call_count == 1
