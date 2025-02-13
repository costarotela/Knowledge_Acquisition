"""
Schema definitions for YouTube Agent.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

class VideoMetadata(BaseModel):
    """YouTube video metadata."""
    video_id: str
    title: str
    description: Optional[str] = None
    channel_id: str
    channel_name: str
    publish_date: Optional[datetime] = None
    duration: int  # in seconds
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    language: Optional[str] = None
    quality_score: float = Field(default=0.5, ge=0.0, le=1.0)

class TranscriptSegment(BaseModel):
    """Segment from video transcript."""
    video_id: str
    start: float  # start time in seconds
    duration: float
    text: str
    speaker: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    context: Optional[str] = None

class ContentClaim(BaseModel):
    """Content claim extracted from video."""
    statement: str
    video_id: str
    timestamp: float  # time in video where claim appears
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_segments: List[Dict[str, Any]] = Field(default_factory=list)
    contradicting_segments: List[Dict[str, Any]] = Field(default_factory=list)
    verification_status: str = "unverified"  # unverified, verified, disputed
    domain_context: List[str] = Field(default_factory=list)

class VideoContext(BaseModel):
    """Video analysis context."""
    query: str
    objective: str
    domain: Optional[str] = None
    required_depth: int = Field(default=3, ge=1, le=5)
    time_constraints: Optional[Dict[str, Any]] = None
    content_preferences: Dict[str, float] = Field(default_factory=dict)

class VideoAnalysis(BaseModel):
    """Video analysis results."""
    context: VideoContext
    metadata: VideoMetadata
    key_segments: List[TranscriptSegment] = Field(default_factory=list)
    verified_claims: List[ContentClaim] = Field(default_factory=list)
    insights: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    knowledge_gaps: List[str] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
