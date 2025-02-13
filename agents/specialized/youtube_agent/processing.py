"""
Processing module for YouTube Agent.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import asyncio
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
import nltk
from moviepy.editor import VideoFileClip

from .schemas import (
    VideoMetadata, TranscriptSegment, ContentClaim,
    VideoContext, VideoAnalysis
)

logger = logging.getLogger(__name__)

class YouTubeProcessor:
    """Processor for YouTube content."""
    
    def __init__(self):
        """Initialize processor."""
        try:
            nltk.download('punkt')
            nltk.download('averaged_perceptron_tagger')
            nltk.download('maxent_ne_chunker')
            nltk.download('words')
        except:
            logger.warning("Failed to download NLTK data")
    
    async def extract_metadata(
        self,
        video_id: str
    ) -> Dict[str, Any]:
        """Extract metadata from YouTube video."""
        try:
            # Use pytube to get video info
            url = f"https://www.youtube.com/watch?v={video_id}"
            yt = YouTube(url)
            
            return {
                "success": True,
                "metadata": {
                    "video_id": video_id,
                    "title": yt.title,
                    "description": yt.description,
                    "channel_id": yt.channel_id,
                    "channel_name": yt.author,
                    "publish_date": yt.publish_date,
                    "duration": yt.length,
                    "view_count": yt.views,
                    "tags": yt.keywords or [],
                    "category": yt.category,
                    "language": self._detect_language(yt.title + " " + yt.description)
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting metadata for video {video_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def extract_transcript(
        self,
        video_id: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract transcript from YouTube video."""
        try:
            # Get available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get manual transcript first
            try:
                if language:
                    transcript = transcript_list.find_manually_created_transcript([language])
                else:
                    transcript = transcript_list.find_manually_created_transcript()
            except:
                # Fall back to generated transcript
                if language:
                    transcript = transcript_list.find_generated_transcript([language])
                else:
                    transcript = transcript_list.find_generated_transcript()
            
            # Get transcript data
            transcript_data = transcript.fetch()
            
            # Convert to segments
            segments = []
            for item in transcript_data:
                segments.append({
                    "start": item["start"],
                    "duration": item["duration"],
                    "text": item["text"],
                    "confidence": 0.9 if transcript.is_manually_created else 0.7
                })
            
            return {
                "success": True,
                "segments": segments,
                "language": transcript.language,
                "is_manual": transcript.is_manually_created
            }
            
        except Exception as e:
            logger.error(f"Error extracting transcript for video {video_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_transcript(
        self,
        segments: List[Dict[str, Any]],
        video_id: str,
        context: VideoContext
    ) -> List[TranscriptSegment]:
        """Process transcript into meaningful segments."""
        try:
            processed_segments = []
            current_segment = []
            current_start = None
            current_duration = 0
            
            for segment in segments:
                if not current_start:
                    current_start = segment["start"]
                
                current_segment.append(segment["text"])
                current_duration += segment["duration"]
                
                # Create new segment every 30 seconds or at natural breaks
                if (current_duration >= 30 or
                    segment["text"].strip().endswith('.')):
                    
                    segment_text = ' '.join(current_segment)
                    
                    # Extract named entities for context
                    tokens = nltk.word_tokenize(segment_text)
                    pos_tags = nltk.pos_tag(tokens)
                    named_entities = nltk.ne_chunk(pos_tags)
                    
                    entities = []
                    for chunk in named_entities:
                        if hasattr(chunk, 'label'):
                            entity = ' '.join(c[0] for c in chunk)
                            entity_type = chunk.label()
                            entities.append(f"{entity_type}: {entity}")
                    
                    segment_context = '; '.join(entities) if entities else "No named entities found"
                    
                    # Create segment
                    processed_segments.append(TranscriptSegment(
                        video_id=video_id,
                        start=current_start,
                        duration=current_duration,
                        text=segment_text,
                        confidence=segment["confidence"],
                        relevance_score=self._calculate_relevance(
                            segment_text,
                            context.query,
                            context.objective
                        ),
                        context=segment_context
                    ))
                    
                    current_segment = []
                    current_start = None
                    current_duration = 0
            
            # Add any remaining text
            if current_segment:
                segment_text = ' '.join(current_segment)
                processed_segments.append(TranscriptSegment(
                    video_id=video_id,
                    start=current_start,
                    duration=current_duration,
                    text=segment_text,
                    confidence=segments[-1]["confidence"],
                    relevance_score=self._calculate_relevance(
                        segment_text,
                        context.query,
                        context.objective
                    )
                ))
            
            return processed_segments
            
        except Exception as e:
            logger.error(f"Error processing transcript: {str(e)}")
            return []
    
    async def analyze_video_quality(
        self,
        metadata: Dict[str, Any],
        transcript_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze quality and credibility of video."""
        try:
            # Quality indicators
            indicators = {
                # Metadata-based indicators
                "has_description": bool(metadata.get("description")),
                "has_tags": bool(metadata.get("tags")),
                "has_category": bool(metadata.get("category")),
                "view_count": metadata.get("view_count", 0),
                "duration": metadata.get("duration", 0),
                
                # Transcript-based indicators
                "has_transcript": transcript_info.get("success", False),
                "manual_transcript": transcript_info.get("is_manual", False),
                "transcript_language": transcript_info.get("language"),
                
                # Channel indicators
                "has_channel_info": bool(metadata.get("channel_id"))
            }
            
            # Calculate quality score
            weights = {
                "has_description": 0.15,
                "has_tags": 0.1,
                "has_category": 0.05,
                "has_transcript": 0.2,
                "manual_transcript": 0.2,
                "has_channel_info": 0.1
            }
            
            quality_score = sum(
                weights[key] * (1 if value else 0)
                for key, value in indicators.items()
                if key in weights
            )
            
            # Adjust for view count and duration
            if indicators["view_count"] > 10000:
                quality_score *= 1.2
            if 300 <= indicators["duration"] <= 3600:  # between 5 min and 1 hour
                quality_score *= 1.1
            
            quality_score = min(max(quality_score, 0.1), 1.0)
            
            return {
                "quality_score": quality_score,
                "indicators": indicators
            }
            
        except Exception as e:
            logger.error(f"Error analyzing video quality: {str(e)}")
            return {
                "quality_score": 0.5,
                "error": str(e)
            }
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of text."""
        try:
            from langdetect import detect
            return detect(text)
        except:
            return None
    
    def _calculate_relevance(
        self,
        text: str,
        query: str,
        objective: str
    ) -> float:
        """Calculate relevance score for text."""
        try:
            # Simple relevance calculation based on term overlap
            text_terms = set(nltk.word_tokenize(text.lower()))
            query_terms = set(nltk.word_tokenize(query.lower()))
            objective_terms = set(nltk.word_tokenize(objective.lower()))
            
            query_overlap = len(text_terms & query_terms) / len(query_terms)
            objective_overlap = len(text_terms & objective_terms) / len(objective_terms)
            
            # Weight query match higher than objective match
            relevance = (0.7 * query_overlap) + (0.3 * objective_overlap)
            
            return min(max(relevance, 0.0), 1.0)
            
        except:
            return 0.5
