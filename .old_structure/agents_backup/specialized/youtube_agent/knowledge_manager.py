"""
Knowledge management for YouTube Agent.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .schemas import (
    VideoMetadata, TranscriptSegment, ContentClaim,
    VideoContext, VideoAnalysis
)

logger = logging.getLogger(__name__)

class YouTubeKnowledgeManager:
    """Manager for YouTube content knowledge."""
    
    def __init__(
        self,
        vector_store_path: str,
        embeddings: Optional[OpenAIEmbeddings] = None
    ):
        """Initialize knowledge manager."""
        self.embeddings = embeddings or OpenAIEmbeddings()
        self.vector_store = Chroma(
            persist_directory=vector_store_path,
            embedding_function=self.embeddings
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    async def store_video_analysis(
        self,
        analysis: VideoAnalysis,
        synthesis_results: Dict[str, Any]
    ) -> bool:
        """Store video analysis results."""
        try:
            # Store video metadata
            await self._store_metadata(analysis.metadata)
            
            # Store key segments
            await self._store_segments(analysis.key_segments)
            
            # Store verified claims
            await self._store_claims(analysis.verified_claims)
            
            # Store analysis results
            await self._store_synthesis_results(analysis, synthesis_results)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing video analysis: {str(e)}")
            return False
    
    async def _store_metadata(self, metadata: VideoMetadata):
        """Store video metadata in vector store."""
        document = {
            "text": f"""
            Title: {metadata.title}
            Description: {metadata.description or 'No description'}
            Channel: {metadata.channel_name}
            Category: {metadata.category or 'Unknown'}
            Tags: {', '.join(metadata.tags)}
            """,
            "metadata": {
                "video_id": metadata.video_id,
                "channel_id": metadata.channel_id,
                "publish_date": metadata.publish_date.isoformat() if metadata.publish_date else None,
                "duration": metadata.duration,
                "quality_score": metadata.quality_score,
                "type": "video_metadata"
            }
        }
        
        self.vector_store.add_texts(
            texts=[document["text"]],
            metadatas=[document["metadata"]]
        )
    
    async def _store_segments(self, segments: List[TranscriptSegment]):
        """Store transcript segments in vector store."""
        documents = []
        
        for segment in segments:
            # Split text into chunks if needed
            chunks = self.text_splitter.split_text(segment.text)
            
            # Create documents with metadata
            documents.extend([{
                "text": chunk,
                "metadata": {
                    "video_id": segment.video_id,
                    "start": segment.start,
                    "duration": segment.duration,
                    "confidence": segment.confidence,
                    "relevance_score": segment.relevance_score,
                    "context": segment.context,
                    "type": "transcript_segment"
                }
            } for chunk in chunks])
        
        if documents:
            texts = [d["text"] for d in documents]
            metadatas = [d["metadata"] for d in documents]
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
    
    async def _store_claims(self, claims: List[ContentClaim]):
        """Store content claims in vector store."""
        documents = []
        
        for claim in claims:
            documents.append({
                "text": claim.statement,
                "metadata": {
                    "video_id": claim.video_id,
                    "timestamp": claim.timestamp,
                    "confidence_score": claim.confidence_score,
                    "verification_status": claim.verification_status,
                    "domain_context": claim.domain_context,
                    "type": "content_claim"
                }
            })
        
        if documents:
            texts = [d["text"] for d in documents]
            metadatas = [d["metadata"] for d in documents]
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
    
    async def _store_synthesis_results(
        self,
        analysis: VideoAnalysis,
        results: Dict[str, Any]
    ):
        """Store analysis synthesis results."""
        documents = []
        
        # Store analysis context
        documents.append({
            "text": f"""
            Query: {analysis.context.query}
            Objective: {analysis.context.objective}
            Domain: {analysis.context.domain or 'General'}
            """,
            "metadata": {
                "video_id": analysis.metadata.video_id,
                "type": "analysis_context",
                "required_depth": analysis.context.required_depth,
                "time_constraints": analysis.context.time_constraints
            }
        })
        
        # Store key findings
        if "key_findings" in results:
            for finding in results["key_findings"]:
                documents.append({
                    "text": finding["finding"],
                    "metadata": {
                        "video_id": analysis.metadata.video_id,
                        "type": "key_finding",
                        "confidence": finding["confidence"],
                        "implications": finding["implications"]
                    }
                })
        
        # Store content gaps
        if "content_gaps" in results:
            for gap in results["content_gaps"]:
                documents.append({
                    "text": gap["gap"],
                    "metadata": {
                        "video_id": analysis.metadata.video_id,
                        "type": "content_gap",
                        "impact": gap["impact"],
                        "suggestions": gap["suggestions"]
                    }
                })
        
        if documents:
            texts = [d["text"] for d in documents]
            metadatas = [d["metadata"] for d in documents]
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
    
    async def query_knowledge(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Query stored knowledge."""
        try:
            results = self.vector_store.similarity_search(
                query,
                filter=filters,
                k=limit
            )
            
            return [{
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity": doc.similarity
            } for doc in results]
            
        except Exception as e:
            logger.error(f"Error querying knowledge: {str(e)}")
            return []
    
    async def validate_claim(
        self,
        claim: ContentClaim
    ) -> Dict[str, Any]:
        """Validate a content claim."""
        try:
            # Query similar claims
            similar = await self.query_knowledge(
                claim.statement,
                filters={"type": "content_claim"},
                limit=3
            )
            
            # Check for support and contradictions
            supporting = []
            contradicting = []
            
            for item in similar:
                if item["similarity"] > 0.8:
                    supporting.append(item)
                elif item["similarity"] > 0.5:
                    # Check for contradictions
                    if self._contradicts(claim.statement, item["content"]):
                        contradicting.append(item)
            
            # Calculate confidence
            confidence = claim.confidence_score
            if supporting:
                confidence = min(
                    confidence + len(supporting) * 0.1,
                    1.0
                )
            if contradicting:
                confidence = max(
                    confidence - len(contradicting) * 0.2,
                    0.1
                )
            
            return {
                "valid": len(contradicting) == 0,
                "confidence": confidence,
                "supporting_evidence": supporting,
                "contradicting_evidence": contradicting,
                "verification_status": (
                    "verified" if len(supporting) > 0 and len(contradicting) == 0
                    else "disputed" if len(contradicting) > 0
                    else "unverified"
                )
            }
            
        except Exception as e:
            logger.error(f"Error validating claim: {str(e)}")
            return {
                "valid": False,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _contradicts(self, statement1: str, statement2: str) -> bool:
        """Check if two statements contradict each other."""
        # Simple contradiction check
        # TODO: Implement more sophisticated contradiction detection
        negation_words = {"not", "no", "never", "false", "incorrect", "wrong"}
        
        has_negation1 = any(word in statement1.lower() for word in negation_words)
        has_negation2 = any(word in statement2.lower() for word in negation_words)
        
        return has_negation1 != has_negation2
