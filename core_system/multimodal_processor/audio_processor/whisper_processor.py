"""
Whisper-based audio processor for speech recognition and transcription.
"""
import torch
from faster_whisper import WhisperModel
from typing import List, Dict, Any, Optional
import logging
import numpy as np
from pydub import AudioSegment
import os

from ..base import BaseProcessor, AudioContent, ProcessingResult

logger = logging.getLogger(__name__)

class WhisperProcessor(BaseProcessor):
    """Audio processor using Whisper for transcription and analysis."""
    
    SUPPORTED_FORMATS = {'.wav', '.mp3', '.ogg', '.flac', '.m4a'}
    
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        compute_type: str = "float16" if torch.cuda.is_available() else "float32"
    ):
        """Initialize Whisper processor."""
        logger.info(f"Initializing Whisper processor with device: {device}")
        
        self.device = device
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
    
    async def validate_source(self, source: str) -> bool:
        """Validate if the source is a supported audio file."""
        try:
            extension = os.path.splitext(source)[1].lower()
            return extension in self.SUPPORTED_FORMATS
        except Exception:
            return False
    
    async def extract_content(self, source: str) -> AudioContent:
        """Extract content from audio source."""
        try:
            # Load audio file
            audio = AudioSegment.from_file(source)
            
            return AudioContent(
                source_url=source,
                source_type="audio",
                duration=len(audio) / 1000.0,  # Convert to seconds
                transcript="",  # Will be filled during processing
                segments=[],
                metadata={
                    "format": os.path.splitext(source)[1][1:],
                    "channels": audio.channels,
                    "sample_width": audio.sample_width,
                    "frame_rate": audio.frame_rate
                }
            )
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            raise
    
    async def detect_language(self, audio_path: str) -> str:
        """Detect the language of the audio."""
        try:
            # Use a small segment for language detection
            segments, info = self.model.transcribe(
                audio_path,
                language=None,  # Auto-detect
                task="translate"
            )
            
            return info.language
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            raise
    
    async def process_content(self, content: AudioContent) -> ProcessingResult:
        """Process the audio content."""
        try:
            # Detect language if not already set
            if not content.language:
                content.language = await self.detect_language(content.source_url)
            
            # Transcribe with detected language
            segments, info = self.model.transcribe(
                content.source_url,
                language=content.language,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=400
                )
            )
            
            # Process segments
            processed_segments = []
            full_transcript = []
            confidence_scores = {}
            
            for segment in segments:
                processed_segment = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "words": [
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability
                        }
                        for word in segment.words
                    ]
                }
                
                processed_segments.append(processed_segment)
                full_transcript.append(segment.text)
                
                # Calculate confidence for segment
                word_probabilities = [word.probability for word in segment.words]
                confidence_scores[f"segment_{len(processed_segments)}"] = float(np.mean(word_probabilities))
            
            # Update content with transcription
            content.transcript = " ".join(full_transcript)
            content.segments = processed_segments
            
            # Add overall confidence score
            confidence_scores["overall"] = float(np.mean(list(confidence_scores.values())))
            
            return ProcessingResult(
                content_type="audio",
                raw_content=content,
                extracted_knowledge=[{
                    "transcript": content.transcript,
                    "segments": processed_segments,
                    "language": content.language,
                    "duration": content.duration
                }],
                confidence_scores=confidence_scores,
                processing_metadata={
                    "model": "whisper-large-v3",
                    "device": self.device,
                    "language": content.language,
                    "audio_format": content.metadata.get("format"),
                    "total_segments": len(processed_segments)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in content processing: {e}")
            raise
    
    def _segment_audio(self, audio: AudioSegment, segment_length: int = 30000) -> List[AudioSegment]:
        """Segment audio into chunks for processing."""
        segments = []
        for start in range(0, len(audio), segment_length):
            end = min(start + segment_length, len(audio))
            segment = audio[start:end]
            segments.append(segment)
        return segments
