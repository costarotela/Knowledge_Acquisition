"""
Specialized agent for acquiring knowledge from YouTube.
"""
from typing import Dict, Any, List, Optional
import logging
from pytube import YouTube
import os
import json

from ..base_agents.knowledge_agent import KnowledgeAgent
from core_system.agent_orchestrator.base import Task, TaskResult

logger = logging.getLogger(__name__)

class YouTubeAgent(KnowledgeAgent):
    """Agent specialized in extracting knowledge from YouTube videos."""
    
    def __init__(self, *args, **kwargs):
        """Initialize YouTube agent."""
        super().__init__(*args, **kwargs)
        
        # YouTube-specific settings
        self.download_path = self.config.get("download_path", "/tmp/youtube")
        self.supported_formats = self.config.get("supported_formats", ["mp4", "webm"])
        self.max_duration = self.config.get("max_duration", 3600)  # 1 hour
        
        # Create download directory
        os.makedirs(self.download_path, exist_ok=True)
    
    async def _process_extraction(self, task: Task) -> TaskResult:
        """Process YouTube video extraction."""
        try:
            url = task.input_data["source_url"]
            extraction_type = task.input_data["extraction_type"]
            
            # Download and process video
            video_path = await self._download_video(url)
            if not video_path:
                return TaskResult(
                    success=False,
                    error="Failed to download video"
                )
            
            # Process video content
            processed_data = await self._process_media(video_path)
            if not processed_data:
                return TaskResult(
                    success=False,
                    error="Failed to process video"
                )
            
            # Extract knowledge based on type
            if extraction_type == "transcript":
                knowledge = await self._extract_transcript(processed_data)
            elif extraction_type == "visual":
                knowledge = await self._extract_visual(processed_data)
            elif extraction_type == "combined":
                knowledge = await self._extract_combined(processed_data)
            else:
                return TaskResult(
                    success=False,
                    error=f"Unsupported extraction type: {extraction_type}"
                )
            
            # Store extracted knowledge
            success = await self._store_knowledge(
                knowledge["items"],
                knowledge["confidence_scores"]
            )
            
            if not success:
                return TaskResult(
                    success=False,
                    error="Failed to store knowledge"
                )
            
            # Cleanup
            os.remove(video_path)
            
            return TaskResult(
                success=True,
                data=knowledge,
                metrics={
                    "video_duration": processed_data["content"].duration,
                    "items_extracted": len(knowledge["items"]),
                    "avg_confidence": sum(knowledge["confidence_scores"].values()) / len(knowledge["confidence_scores"])
                }
            )
            
        except Exception as e:
            logger.error(f"Error in YouTube extraction: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )
    
    async def _process_validation(self, task: Task) -> TaskResult:
        """Validate extracted YouTube knowledge."""
        try:
            knowledge_id = task.input_data["knowledge_id"]
            validation_type = task.input_data["validation_type"]
            
            # Get knowledge to validate
            knowledge = await self.knowledge_store.get_knowledge(knowledge_id)
            if not knowledge:
                return TaskResult(
                    success=False,
                    error=f"Knowledge not found: {knowledge_id}"
                )
            
            # Perform validation
            if validation_type == "consistency":
                validation = await self._validate_consistency(knowledge)
            elif validation_type == "completeness":
                validation = await self._validate_completeness(knowledge)
            elif validation_type == "accuracy":
                validation = await self._validate_accuracy(knowledge)
            else:
                return TaskResult(
                    success=False,
                    error=f"Unsupported validation type: {validation_type}"
                )
            
            return TaskResult(
                success=True,
                data=validation,
                metrics={
                    "validation_score": validation["score"],
                    "issues_found": len(validation["issues"])
                }
            )
            
        except Exception as e:
            logger.error(f"Error in YouTube validation: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )
    
    async def _process_enrichment(self, task: Task) -> TaskResult:
        """Enrich YouTube knowledge."""
        try:
            knowledge_id = task.input_data["knowledge_id"]
            enrichment_type = task.input_data["enrichment_type"]
            
            # Get knowledge to enrich
            enriched = await self._enrich_knowledge(
                knowledge_id,
                enrichment_type
            )
            
            if not enriched:
                return TaskResult(
                    success=False,
                    error="Failed to enrich knowledge"
                )
            
            return TaskResult(
                success=True,
                data=enriched,
                metrics={
                    "enriched_fields": len(enriched.get("added_fields", [])),
                    "enrichment_score": enriched.get("enrichment_score", 0)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in YouTube enrichment: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )
    
    async def _download_video(self, url: str) -> Optional[str]:
        """Download YouTube video."""
        try:
            # Create YouTube object
            yt = YouTube(url)
            
            # Validate duration
            if yt.length > self.max_duration:
                logger.error(f"Video too long: {yt.length} seconds")
                return None
            
            # Get best stream
            stream = yt.streams.filter(
                progressive=True,
                file_extension="mp4"
            ).order_by("resolution").desc().first()
            
            if not stream:
                return None
            
            # Download video
            video_path = stream.download(
                output_path=self.download_path,
                filename=f"{yt.video_id}.mp4"
            )
            
            return video_path
            
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    async def _extract_transcript(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract knowledge from video transcript."""
        try:
            transcript = processed_data["extracted_data"][0]["transcript"]
            segments = processed_data["extracted_data"][0]["segments"]
            
            knowledge_items = []
            confidence_scores = {}
            
            # Process each segment
            for i, segment in enumerate(segments):
                item = {
                    "type": "transcript_segment",
                    "content": segment["text"],
                    "start_time": segment["start"],
                    "end_time": segment["end"],
                    "speaker": segment.get("speaker"),
                    "metadata": {
                        "words": segment["words"],
                        "language": processed_data["content"].language
                    }
                }
                
                knowledge_items.append(item)
                confidence_scores[f"item_{i}"] = segment.get("confidence", 0.0)
            
            return {
                "items": knowledge_items,
                "confidence_scores": confidence_scores
            }
            
        except Exception as e:
            logger.error(f"Error extracting transcript: {e}")
            raise
    
    async def _extract_visual(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract knowledge from video visuals."""
        try:
            frames = processed_data["extracted_data"]
            
            knowledge_items = []
            confidence_scores = {}
            
            # Process each frame
            for i, frame in enumerate(frames):
                item = {
                    "type": "visual_frame",
                    "timestamp": frame["timestamp"],
                    "scene_description": frame["scene_description"],
                    "objects": frame["detected_objects"],
                    "actions": frame["detected_actions"],
                    "text": frame["detected_text"],
                    "metadata": {
                        "context": frame["context"]
                    }
                }
                
                knowledge_items.append(item)
                confidence_scores[f"item_{i}"] = processed_data["confidence_scores"].get(
                    f"frame_{frame['timestamp']}", 0.0
                )
            
            return {
                "items": knowledge_items,
                "confidence_scores": confidence_scores
            }
            
        except Exception as e:
            logger.error(f"Error extracting visuals: {e}")
            raise
    
    async def _extract_combined(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract combined knowledge from video."""
        try:
            # Get transcript and visual knowledge
            transcript = await self._extract_transcript(processed_data)
            visual = await self._extract_visual(processed_data)
            
            # Combine knowledge
            combined_items = []
            combined_scores = {}
            
            # Align transcript with visual frames
            for i, (t_item, v_item) in enumerate(zip(
                transcript["items"],
                visual["items"]
            )):
                combined_item = {
                    "type": "multimodal_segment",
                    "timestamp": v_item["timestamp"],
                    "transcript": t_item["content"],
                    "visual_description": v_item["scene_description"],
                    "objects": v_item["objects"],
                    "actions": v_item["actions"],
                    "metadata": {
                        "transcript_metadata": t_item["metadata"],
                        "visual_metadata": v_item["metadata"]
                    }
                }
                
                combined_items.append(combined_item)
                
                # Average confidence scores
                t_score = transcript["confidence_scores"][f"item_{i}"]
                v_score = visual["confidence_scores"][f"item_{i}"]
                combined_scores[f"item_{i}"] = (t_score + v_score) / 2
            
            return {
                "items": combined_items,
                "confidence_scores": combined_scores
            }
            
        except Exception as e:
            logger.error(f"Error extracting combined knowledge: {e}")
            raise
    
    async def _validate_consistency(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Validate knowledge consistency."""
        issues = []
        score = 1.0
        
        # Check for temporal consistency
        timestamps = []
        for item in knowledge.get("items", []):
            if "timestamp" in item:
                timestamps.append(item["timestamp"])
        
        if timestamps != sorted(timestamps):
            issues.append("Temporal sequence is inconsistent")
            score *= 0.8
        
        # Check for content consistency
        prev_desc = None
        for item in knowledge.get("items", []):
            if "visual_description" in item:
                curr_desc = item["visual_description"]
                if prev_desc and curr_desc:
                    # Simple similarity check
                    if len(set(curr_desc.split()) & set(prev_desc.split())) < 2:
                        issues.append(f"Scene description discontinuity at {item['timestamp']}")
                        score *= 0.9
                prev_desc = curr_desc
        
        return {
            "score": score,
            "issues": issues,
            "validation_type": "consistency"
        }
    
    async def _validate_completeness(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Validate knowledge completeness."""
        issues = []
        score = 1.0
        
        required_fields = ["timestamp", "transcript", "visual_description"]
        
        for i, item in enumerate(knowledge.get("items", [])):
            missing_fields = [f for f in required_fields if f not in item]
            if missing_fields:
                issues.append(f"Missing fields {missing_fields} in item {i}")
                score *= 0.9
            
            # Check for empty or minimal content
            for field in ["transcript", "visual_description"]:
                if field in item and len(item[field].split()) < 3:
                    issues.append(f"Minimal content in {field} for item {i}")
                    score *= 0.95
        
        return {
            "score": score,
            "issues": issues,
            "validation_type": "completeness"
        }
    
    async def _validate_accuracy(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Validate knowledge accuracy."""
        issues = []
        score = 1.0
        
        for i, item in enumerate(knowledge.get("items", [])):
            # Check confidence scores
            if f"item_{i}" in knowledge.get("confidence_scores", {}):
                conf_score = knowledge["confidence_scores"][f"item_{i}"]
                if conf_score < 0.7:
                    issues.append(f"Low confidence ({conf_score}) for item {i}")
                    score *= conf_score
            
            # Check for contradictions
            if "transcript" in item and "visual_description" in item:
                transcript_objects = set(item["transcript"].lower().split())
                visual_objects = set(item.get("objects", []))
                
                # Simple contradiction check
                common_objects = transcript_objects & visual_objects
                if not common_objects:
                    issues.append(f"No overlap between transcript and visual objects in item {i}")
                    score *= 0.9
        
        return {
            "score": score,
            "issues": issues,
            "validation_type": "accuracy"
        }
    
    async def _enrich_semantic(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich with semantic information."""
        enriched_items = []
        added_fields = set()
        
        for item in knowledge.get("items", []):
            # Add semantic categories
            if "objects" in item:
                item["object_categories"] = await self._categorize_objects(item["objects"])
                added_fields.add("object_categories")
            
            # Add action categories
            if "actions" in item:
                item["action_categories"] = await self._categorize_actions(item["actions"])
                added_fields.add("action_categories")
            
            enriched_items.append(item)
        
        return {
            "items": enriched_items,
            "added_fields": list(added_fields),
            "enrichment_score": 0.8 if added_fields else 0.0
        }
    
    async def _enrich_temporal(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich with temporal information."""
        enriched_items = []
        added_fields = set()
        
        prev_item = None
        for item in knowledge.get("items", []):
            # Add temporal relations
            if prev_item:
                item["temporal_relation"] = self._get_temporal_relation(prev_item, item)
                added_fields.add("temporal_relation")
            
            # Add duration information
            if "start_time" in item and "end_time" in item:
                item["duration"] = item["end_time"] - item["start_time"]
                added_fields.add("duration")
            
            enriched_items.append(item)
            prev_item = item
        
        return {
            "items": enriched_items,
            "added_fields": list(added_fields),
            "enrichment_score": 0.9 if added_fields else 0.0
        }
    
    async def _enrich_relational(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich with relational information."""
        enriched_items = []
        added_fields = set()
        
        for item in knowledge.get("items", []):
            # Add object relations
            if "objects" in item:
                item["object_relations"] = await self._extract_object_relations(item)
                added_fields.add("object_relations")
            
            # Add action relations
            if "actions" in item:
                item["action_relations"] = await self._extract_action_relations(item)
                added_fields.add("action_relations")
            
            enriched_items.append(item)
        
        return {
            "items": enriched_items,
            "added_fields": list(added_fields),
            "enrichment_score": 0.85 if added_fields else 0.0
        }
    
    async def _categorize_objects(self, objects: List[str]) -> Dict[str, List[str]]:
        """Categorize detected objects."""
        # Implement object categorization logic
        return {"placeholder": objects}
    
    async def _categorize_actions(self, actions: List[str]) -> Dict[str, List[str]]:
        """Categorize detected actions."""
        # Implement action categorization logic
        return {"placeholder": actions}
    
    def _get_temporal_relation(
        self,
        prev_item: Dict[str, Any],
        curr_item: Dict[str, Any]
    ) -> str:
        """Get temporal relation between items."""
        if "timestamp" not in prev_item or "timestamp" not in curr_item:
            return "unknown"
        
        time_diff = curr_item["timestamp"] - prev_item["timestamp"]
        
        if time_diff < 1:
            return "immediate"
        elif time_diff < 5:
            return "very_close"
        elif time_diff < 30:
            return "close"
        else:
            return "distant"
    
    async def _extract_object_relations(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract relations between objects."""
        # Implement object relation extraction logic
        return []
    
    async def _extract_action_relations(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract relations between actions."""
        # Implement action relation extraction logic
        return []
