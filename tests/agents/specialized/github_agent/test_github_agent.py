"""
Tests for GitHub Agent.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import aiohttp
import json

from agents.specialized.github_agent.github_agent import GitHubAgent
from agents.specialized.github_agent.schemas import (
    RepoContext, CodeFragment, IssueInfo,
    CommitInfo, RepositoryKnowledge
)
from core_system.agent_orchestrator.base import Task, TaskResult

@pytest.fixture
def mock_response():
    """Create mock response."""
    class MockResponse:
        def __init__(self, data):
            self._data = data
        
        async def json(self):
            return self._data
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc, tb):
            pass
    
    return MockResponse

@pytest.fixture
def mock_session(mock_response):
    """Create mock session."""
    class MockSession:
        def __init__(self, responses):
            self.responses = responses
            self.closed = False
        
        def get(self, url):
            return mock_response(self.responses.get(url, {}))
        
        async def close(self):
            self.closed = True
    
    return MockSession

@pytest.fixture
def sample_repo_data():
    """Sample repository data."""
    return {
        "description": "Test repo",
        "stargazers_count": 100,
        "forks_count": 50,
        "updated_at": "2024-02-13T00:00:00Z",
        "topics": ["python", "testing"],
        "default_branch": "main"
    }

@pytest.mark.asyncio
async def test_github_agent_initialization():
    """Test GitHub agent initialization."""
    agent = GitHubAgent(config={"github_token": "test_token"})
    assert agent.api_token == "test_token"
    assert agent.max_files == 100  # default value
    
    success = await agent.initialize()
    assert success
    assert agent.processor is not None

@pytest.mark.asyncio
async def test_process_task_with_url(mock_session, sample_repo_data):
    """Test processing task with GitHub URL."""
    # Setup mock responses
    responses = {
        "https://api.github.com/repos/owner/repo": sample_repo_data,
        "https://api.github.com/repos/owner/repo/languages": {"Python": 1000},
        "https://api.github.com/repos/owner/repo/git/trees/main?recursive=1": {
            "tree": []
        },
        "https://api.github.com/repos/owner/repo/issues?state=all": [],
        "https://api.github.com/repos/owner/repo/commits": []
    }
    
    with patch("aiohttp.ClientSession", return_value=mock_session(responses)):
        agent = GitHubAgent(config={"github_token": "test_token"})
        await agent.initialize()
        
        task = Task(
            id="test",
            type="analyze_repo",
            input={"url": "https://github.com/owner/repo"}
        )
        
        result = await agent.process_task(task)
        
        assert result.success
        assert result.result["context"]["owner"] == "owner"
        assert result.result["context"]["name"] == "repo"
        assert result.confidence > 0

@pytest.mark.asyncio
async def test_process_task_with_invalid_input():
    """Test processing task with invalid input."""
    agent = GitHubAgent(config={"github_token": "test_token"})
    await agent.initialize()
    
    task = Task(
        id="test",
        type="analyze_repo",
        input={"invalid": "input"}
    )
    
    result = await agent.process_task(task)
    
    assert not result.success
    assert "No repository information found" in result.error

@pytest.mark.asyncio
async def test_cleanup():
    """Test agent cleanup."""
    agent = GitHubAgent(config={"github_token": "test_token"})
    await agent.initialize()
    
    # Mock session
    agent.processor.session = Mock()
    agent.processor.session.close = Mock()
    
    await agent.cleanup()
    
    agent.processor.session.close.assert_called_once()
