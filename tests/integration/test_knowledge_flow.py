import pytest
from unittest.mock import Mock, patch
from core_system.agent_orchestrator import AgentOrchestrator
from core_system.knowledge_base import UnifiedKnowledgeStore
from agents.specialized.rag_agent import RAGAgent
from core_system.learning.researchers import WebResearcher

@pytest.fixture
def test_environment():
    """Set up a complete test environment with all components"""
    knowledge_store = UnifiedKnowledgeStore()
    orchestrator = AgentOrchestrator()
    rag_agent = RAGAgent(knowledge_store=knowledge_store)
    web_researcher = WebResearcher()
    
    orchestrator.register_agent(rag_agent)
    
    return {
        "knowledge_store": knowledge_store,
        "orchestrator": orchestrator,
        "rag_agent": rag_agent,
        "web_researcher": web_researcher
    }

def test_complete_knowledge_flow():
    """Test the complete flow of knowledge acquisition and processing"""
    env = test_environment()
    
    # 1. Web researcher finds information
    research_results = env["web_researcher"].execute_search(
        topic="machine learning applications"
    )
    
    # 2. RAG agent processes the information
    processed_knowledge = env["rag_agent"].process_knowledge(research_results)
    
    # 3. Knowledge is stored
    env["knowledge_store"].store_knowledge(processed_knowledge)
    
    # 4. Knowledge can be retrieved and reasoned about
    query_results = env["knowledge_store"].query_knowledge(
        "What are the main applications of machine learning?"
    )
    
    assert len(query_results) > 0
    assert query_results[0]["confidence"] > 0.8

def test_multiagent_collaboration():
    """Test collaboration between multiple agents"""
    env = test_environment()
    
    # Create a complex task that requires multiple agents
    task = {
        "type": "research_and_analyze",
        "topic": "quantum computing",
        "requirements": ["technical_validation", "source_verification"]
    }
    
    # Orchestrator should distribute subtasks to appropriate agents
    env["orchestrator"].process_task(task)
    
    # Verify that multiple agents were involved
    assert len(env["orchestrator"].get_task_history()) > 1

def test_error_recovery():
    """Test system's ability to recover from errors"""
    env = test_environment()
    
    # Simulate a failed web search
    with patch.object(env["web_researcher"], "execute_search", side_effect=Exception("Network error")):
        task = {
            "type": "research",
            "topic": "AI safety"
        }
        
        # System should handle the error and try alternative approaches
        result = env["orchestrator"].process_task(task)
        
        assert result["status"] == "completed"
        assert result["used_fallback"] == True

def test_knowledge_validation():
    """Test end-to-end knowledge validation"""
    env = test_environment()
    
    # Create some potentially conflicting knowledge
    knowledge_items = [
        {
            "text": "AI systems are completely safe",
            "confidence": 0.6,
            "source": "blog"
        },
        {
            "text": "AI systems require careful safety considerations",
            "confidence": 0.9,
            "source": "research_paper"
        }
    ]
    
    # System should properly validate and reconcile conflicts
    validated_knowledge = env["rag_agent"].validate_knowledge(knowledge_items)
    
    assert len(validated_knowledge) == 1
    assert validated_knowledge[0]["confidence"] > 0.8
