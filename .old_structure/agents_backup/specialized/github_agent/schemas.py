"""
Schema definitions for GitHub Agent.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class RepoContext(BaseModel):
    """Repository context information."""
    owner: str
    name: str
    description: Optional[str] = None
    stars: int = 0
    forks: int = 0
    last_update: datetime
    topics: List[str] = Field(default_factory=list)
    languages: Dict[str, int] = Field(default_factory=dict)

class CodeFragment(BaseModel):
    """Code fragment from repository."""
    path: str
    content: str
    language: str
    start_line: int
    end_line: int
    commit_hash: str
    last_modified: datetime
    author: str
    relevance_score: float = 0.0

class IssueInfo(BaseModel):
    """GitHub issue information."""
    number: int
    title: str
    body: str
    state: str
    author: str
    created_at: datetime
    closed_at: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    comments: List[Dict[str, Any]] = Field(default_factory=list)

class CommitInfo(BaseModel):
    """Git commit information."""
    hash: str
    message: str
    author: str
    date: datetime
    files_changed: List[str]
    stats: Dict[str, int]
    relevance_score: float = 0.0

class RepositoryKnowledge(BaseModel):
    """Aggregated knowledge about a repository."""
    context: RepoContext
    key_files: List[CodeFragment] = Field(default_factory=list)
    important_issues: List[IssueInfo] = Field(default_factory=list)
    significant_commits: List[CommitInfo] = Field(default_factory=list)
    documentation: Dict[str, str] = Field(default_factory=dict)
    insights: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = 0.0
