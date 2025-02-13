"""
Unified processor that coordinates multimodal processing.
"""
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
import mimetypes
import asyncio

from .base import BaseProcessor, ProcessingResult, MediaContent
from .vision_models.llava_processor import LLaVAProcessor
from .audio_processor.whisper_processor import WhisperProcessor
from .document_parser.unstructured_processor import UnstructuredProcessor

logger = logging.getLogger(__name__)

class UnifiedProcessor:
    """
    Coordinates processing across different modalities.
    
    This processor:
    1. Detects content type
    2. Routes to appropriate processor
    3. Combines results when needed
    4. Provides unified interface for all media types
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize processors based on configuration."""
        self.config = config
        
        # Initialize processors
        self.processors: Dict[str, BaseProcessor] = {}
        
        # Vision processor
        if config.get("vision", {}).get("enabled", True):
            self.processors["vision"] = LLaVAProcessor(
                model_path=config["vision"].get("model_path", "llava-hf/llava-1.5-7b-hf"),
                device=config["vision"].get("device", "cuda")
            )
        
        # Audio processor
        if config.get("audio", {}).get("enabled", True):
            self.processors["audio"] = WhisperProcessor(
                model_size=config["audio"].get("model_type", "large-v3"),
                device=config["audio"].get("device", "cuda")
            )
        
        # Document processor
        if config.get("document", {}).get("enabled", True):
            self.processors["document"] = UnstructuredProcessor(
                config=config.get("document", {})
            )
    
    async def detect_content_type(self, source: str) -> str:
        """Detect the type of content from the source."""
        try:
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(source)
            
            if not mime_type:
                raise ValueError(f"Could not determine content type for: {source}")
            
            # Map MIME type to processor type
            if mime_type.startswith("video/") or mime_type.startswith("image/"):
                return "vision"
            elif mime_type.startswith("audio/"):
                return "audio"
            elif mime_type.startswith(("text/", "application/")):
                return "document"
            else:
                raise ValueError(f"Unsupported content type: {mime_type}")
                
        except Exception as e:
            logger.error(f"Error detecting content type: {e}")
            raise
    
    async def validate_source(self, source: str) -> bool:
        """Validate if the source can be processed by any processor."""
        try:
            content_type = await self.detect_content_type(source)
            processor = self.processors.get(content_type)
            
            if not processor:
                return False
            
            return await processor.validate_source(source)
            
        except Exception:
            return False
    
    async def process_batch(
        self,
        sources: List[str],
        max_concurrent: int = 3
    ) -> List[ProcessingResult]:
        """
        Process multiple sources concurrently.
        
        Args:
            sources: List of source paths/URLs
            max_concurrent: Maximum number of concurrent processing tasks
            
        Returns:
            List of processing results
        """
        async def process_one(source: str) -> Optional[ProcessingResult]:
            try:
                return await self.process(source)
            except Exception as e:
                logger.error(f"Error processing {source}: {e}")
                return None
        
        # Process in batches
        results = []
        for i in range(0, len(sources), max_concurrent):
            batch = sources[i:i + max_concurrent]
            batch_results = await asyncio.gather(
                *[process_one(source) for source in batch]
            )
            results.extend([r for r in batch_results if r is not None])
        
        return results
    
    async def process(self, source: str) -> ProcessingResult:
        """
        Process a single source through appropriate processor.
        
        Args:
            source: Path or URL to the content
            
        Returns:
            Processing result with extracted information
        """
        try:
            # Validate source
            if not await self.validate_source(source):
                raise ValueError(f"Invalid or unsupported source: {source}")
            
            # Detect content type and get processor
            content_type = await self.detect_content_type(source)
            processor = self.processors.get(content_type)
            
            if not processor:
                raise ValueError(f"No processor available for type: {content_type}")
            
            # Process content
            logger.info(f"Processing {source} with {content_type} processor")
            result = await processor.process(source)
            
            # Add unified metadata
            result.processing_metadata.update({
                "processor_type": content_type,
                "source_path": source,
                "unified_processor_version": "1.0.0"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing {source}: {e}")
            raise
    
    @classmethod
    def from_config_file(cls, config_path: str) -> 'UnifiedProcessor':
        """Create UnifiedProcessor from a configuration file."""
        import yaml
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        return cls(config)
