"""
YouTube Agent with Agentic RAG capabilities.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import asyncio

from .processing import YouTubeProcessor
from .reasoning import YouTubeReasoning
from .knowledge_manager import YouTubeKnowledgeManager
from .schemas import (
    VideoMetadata, TranscriptSegment, ContentClaim,
    VideoContext, VideoAnalysis
)

logger = logging.getLogger(__name__)

class YouTubeAgent:
    """YouTube Agent with Agentic RAG capabilities."""
    
    def __init__(
        self,
        vector_store_path: str,
        api_key: Optional[str] = None
    ):
        """Initialize YouTube Agent."""
        self.processor = YouTubeProcessor()
        self.reasoning = YouTubeReasoning()
        self.knowledge_manager = YouTubeKnowledgeManager(vector_store_path)
        self.api_key = api_key
    
    async def analyze_video(
        self,
        context: VideoContext,
        video_id: str
    ) -> VideoAnalysis:
        """Analyze YouTube video."""
        try:
            # Step 1: Analyze video context
            logger.info("Analyzing video context...")
            analysis_strategy = await self.reasoning.analyze_video_context(context)
            
            # Step 2: Extract metadata and transcript
            logger.info("Extracting video content...")
            metadata_data = await self.processor.extract_metadata(video_id)
            if not metadata_data["success"]:
                raise Exception(f"Failed to extract metadata: {metadata_data['error']}")
            
            transcript_data = await self.processor.extract_transcript(
                video_id,
                metadata_data["metadata"].get("language")
            )
            if not transcript_data["success"]:
                raise Exception(f"Failed to extract transcript: {transcript_data['error']}")
            
            # Step 3: Analyze video quality
            logger.info("Analyzing video quality...")
            quality_data = await self.processor.analyze_video_quality(
                metadata_data["metadata"],
                transcript_data
            )
            
            # Create metadata object
            metadata = VideoMetadata(
                video_id=video_id,
                title=metadata_data["metadata"]["title"],
                description=metadata_data["metadata"]["description"],
                channel_id=metadata_data["metadata"]["channel_id"],
                channel_name=metadata_data["metadata"]["channel_name"],
                publish_date=metadata_data["metadata"]["publish_date"],
                duration=metadata_data["metadata"]["duration"],
                view_count=metadata_data["metadata"]["view_count"],
                tags=metadata_data["metadata"]["tags"],
                category=metadata_data["metadata"]["category"],
                language=metadata_data["metadata"]["language"],
                quality_score=quality_data["quality_score"]
            )
            
            # Step 4: Process transcript
            logger.info("Processing transcript...")
            segments = await self.processor.process_transcript(
                transcript_data["segments"],
                video_id,
                context
            )
            
            # Step 5: Extract and verify claims
            logger.info("Extracting and verifying claims...")
            claims = await self.reasoning.extract_and_verify_claims(
                segments,
                video_id
            )
            
            # Step 6: Validate claims against existing knowledge
            logger.info("Validating claims...")
            verified_claims = []
            
            for claim in claims:
                validation = await self.knowledge_manager.validate_claim(claim)
                if validation["valid"]:
                    claim.confidence_score = validation["confidence"]
                    claim.verification_status = validation["verification_status"]
                    verified_claims.append(claim)
            
            # Step 7: Synthesize analysis
            logger.info("Synthesizing analysis...")
            synthesis = await self.reasoning.synthesize_analysis(
                context,
                metadata,
                verified_claims
            )
            
            # Create video analysis
            analysis = VideoAnalysis(
                context=context,
                metadata=metadata,
                key_segments=segments,
                verified_claims=verified_claims,
                insights=synthesis["key_findings"],
                confidence_score=synthesis["confidence_assessment"]["overall_score"],
                knowledge_gaps=[gap["gap"] for gap in synthesis["content_gaps"]],
                recommendations=synthesis["recommendations"]
            )
            
            # Step 8: Store analysis
            logger.info("Storing analysis...")
            await self.knowledge_manager.store_video_analysis(
                analysis,
                synthesis
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing video: {str(e)}")
            raise
    
    async def query_knowledge(
        self,
        query: str,
        filters: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Query stored knowledge."""
        return await self.knowledge_manager.query_knowledge(query, filters)
    
    async def validate_claim(
        self,
        claim: ContentClaim
    ) -> Dict[str, Any]:
        """Validate a content claim against stored knowledge."""
        return await self.knowledge_manager.validate_claim(claim)
