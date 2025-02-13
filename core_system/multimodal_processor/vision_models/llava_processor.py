"""
LLaVA-based vision processor for multimodal understanding.
"""
import torch
from PIL import Image
from transformers import AutoProcessor, LlavaForConditionalGeneration
from typing import List, Dict, Any, Optional
import logging

from ..base import BaseProcessor, VideoContent, ProcessingResult

logger = logging.getLogger(__name__)

class LLaVAProcessor(BaseProcessor):
    """Vision processor using LLaVA for multimodal understanding."""
    
    def __init__(
        self,
        model_path: str = "llava-hf/llava-1.5-7b-hf",
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        """Initialize LLaVA processor."""
        logger.info(f"Initializing LLaVA processor with device: {device}")
        
        self.device = device
        self.processor = AutoProcessor.from_pretrained(model_path)
        self.model = LlavaForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        ).to(device)
        
        # Define analysis prompts
        self.analysis_prompts = {
            "scene": "Describe the main elements and setting of this scene.",
            "objects": "List all important objects visible in this image.",
            "actions": "What actions or activities are happening in this scene?",
            "text": "Read and transcribe any visible text in this image.",
            "context": "What is the overall context or purpose of this scene?"
        }
    
    async def validate_source(self, source: str) -> bool:
        """Validate if the source is a valid image/video file."""
        try:
            # Check if it's an image file
            Image.open(source)
            return True
        except Exception:
            return False
    
    async def extract_content(self, source: str) -> VideoContent:
        """Extract content from image/video source."""
        try:
            # For now, we'll handle single images
            image = Image.open(source)
            
            return VideoContent(
                source_url=source,
                source_type="image",
                title=source.split("/")[-1],
                duration=0.0,  # Single image
                frames=[{
                    "timestamp": 0.0,
                    "image_path": source
                }]
            )
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            raise
    
    async def process_frame(
        self,
        image: Image.Image,
        prompts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Process a single frame/image with LLaVA."""
        try:
            results = {}
            prompts = prompts or list(self.analysis_prompts.values())
            
            for prompt in prompts:
                # Prepare inputs
                inputs = self.processor(
                    images=image,
                    text=prompt,
                    return_tensors="pt"
                ).to(self.device)
                
                # Generate response
                with torch.no_grad():
                    output = self.model.generate(
                        **inputs,
                        max_new_tokens=100,
                        num_beams=3,
                        temperature=0.7
                    )
                
                response = self.processor.decode(output[0], skip_special_tokens=True)
                results[prompt] = response
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            raise
        
    async def process_content(self, content: VideoContent) -> ProcessingResult:
        """Process the video/image content."""
        try:
            all_results = []
            confidence_scores = {}
            
            # Process each frame
            for frame in content.frames:
                image = Image.open(frame["image_path"])
                frame_results = await self.process_frame(image)
                
                # Structure the results
                processed_frame = {
                    "timestamp": frame["timestamp"],
                    "scene_description": frame_results[self.analysis_prompts["scene"]],
                    "detected_objects": frame_results[self.analysis_prompts["objects"]].split(", "),
                    "detected_actions": frame_results[self.analysis_prompts["actions"]].split(", "),
                    "detected_text": frame_results[self.analysis_prompts["text"]],
                    "context": frame_results[self.analysis_prompts["context"]]
                }
                
                all_results.append(processed_frame)
                
                # Simple confidence scoring based on response length and consistency
                confidence_scores[f"frame_{frame['timestamp']}"] = min(
                    1.0,
                    len(processed_frame["scene_description"]) / 200 * 0.5 +
                    len(processed_frame["detected_objects"]) / 10 * 0.3 +
                    len(processed_frame["detected_actions"]) / 5 * 0.2
                )
            
            return ProcessingResult(
                content_type="video",
                raw_content=content,
                extracted_knowledge=all_results,
                confidence_scores=confidence_scores,
                processing_metadata={
                    "model": "llava-1.5-7b",
                    "device": self.device,
                    "frames_processed": len(content.frames)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in content processing: {e}")
            raise
