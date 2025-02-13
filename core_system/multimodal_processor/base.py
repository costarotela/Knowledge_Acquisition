"""
Base classes for multimodal processing.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class MediaContent(BaseModel):
    """Base class for media content."""
    source_url: str
    source_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processed_at: datetime = Field(default_factory=datetime.now)

class VideoContent(MediaContent):
    """Video content with extracted information."""
    title: str
    duration: float
    frames: List[Dict[str, Any]]
    transcript: Optional[str] = None
    scenes: List[Dict[str, Any]] = Field(default_factory=list)
    detected_objects: List[str] = Field(default_factory=list)
    detected_actions: List[str] = Field(default_factory=list)

class AudioContent(MediaContent):
    """Audio content with extracted information."""
    duration: float
    transcript: str
    speakers: List[str] = Field(default_factory=list)
    segments: List[Dict[str, Any]] = Field(default_factory=list)
    language: Optional[str] = None

class DocumentContent(MediaContent):
    """Document content with extracted information."""
    text: str
    format: str
    pages: Optional[int] = None
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    figures: List[Dict[str, Any]] = Field(default_factory=list)

class ProcessingResult(BaseModel):
    """Result of multimodal processing."""
    content_type: str
    raw_content: MediaContent
    extracted_knowledge: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseProcessor(ABC):
    """Abstract base class for media processors."""
    
    @abstractmethod
    async def validate_source(self, source: str) -> bool:
        """Validate if the source can be processed."""
        pass
    
    @abstractmethod
    async def extract_content(self, source: str) -> MediaContent:
        """Extract content from the source."""
        pass
    
    @abstractmethod
    async def process_content(self, content: MediaContent) -> ProcessingResult:
        """Process the extracted content."""
        pass
    
    async def process(self, source: str) -> ProcessingResult:
        """Complete processing pipeline."""
        if not await self.validate_source(source):
            raise ValueError(f"Invalid source: {source}")
        
        content = await self.extract_content(source)
        return await self.process_content(content)
