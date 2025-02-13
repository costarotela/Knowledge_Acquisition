"""
Schema definitions for Web Research Agent.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

class WebSource(BaseModel):
    """Web source information."""
    url: HttpUrl
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    domain: str
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    last_accessed: datetime = Field(default_factory=datetime.now)

class ContentFragment(BaseModel):
    """Content fragment from web source."""
    source_url: HttpUrl
    content: str
    context: str
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    sentiment_score: Optional[float] = None
    extracted_entities: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)

class FactClaim(BaseModel):
    """Fact or claim extracted from content."""
    statement: str
    source_urls: List[HttpUrl]
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    verification_status: str = "unverified"  # unverified, verified, disputed
    domain_context: List[str] = Field(default_factory=list)

class ResearchContext(BaseModel):
    """Research context information."""
    query: str
    objective: str
    domain: Optional[str] = None
    required_depth: int = Field(default=3, ge=1, le=5)
    time_constraints: Optional[Dict[str, Any]] = None
    source_preferences: Dict[str, float] = Field(default_factory=dict)

class ResearchFindings(BaseModel):
    """Aggregated research findings."""
    context: ResearchContext
    sources: List[WebSource] = Field(default_factory=list)
    key_fragments: List[ContentFragment] = Field(default_factory=list)
    verified_facts: List[FactClaim] = Field(default_factory=list)
    insights: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    research_gaps: List[str] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
