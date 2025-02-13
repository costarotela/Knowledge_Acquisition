"""
Reasoning engine for YouTube Agent.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from langchain import PromptTemplate, LLMChain
from langchain.chat_models import ChatOpenAI

from .schemas import (
    VideoMetadata, TranscriptSegment, ContentClaim,
    VideoContext, VideoAnalysis
)

logger = logging.getLogger(__name__)

class YouTubeReasoning:
    """Reasoning engine for YouTube content."""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """Initialize reasoning engine."""
        self.llm = llm or ChatOpenAI(
            model_name="gpt-4",
            temperature=0
        )
    
    async def analyze_video_context(
        self,
        context: VideoContext
    ) -> Dict[str, Any]:
        """Generate video analysis strategy."""
        prompt = PromptTemplate(
            template="""
            Analyze this video research context and generate an analysis strategy:
            
            Query: {query}
            Objective: {objective}
            Domain: {domain}
            Required Depth: {depth}
            
            Generate:
            1. Initial hypotheses about video content
            2. Key aspects to analyze
            3. Content evaluation criteria
            4. Expected insights
            
            Output as JSON:
            {
                "hypotheses": [
                    {
                        "statement": "hypothesis statement",
                        "rationale": "reasoning behind hypothesis",
                        "verification_approach": ["steps to verify"]
                    }
                ],
                "key_aspects": [
                    {
                        "aspect": "specific aspect to analyze",
                        "importance": "high|medium|low",
                        "expected_findings": ["potential findings"]
                    }
                ],
                "evaluation_criteria": {
                    "content_quality": ["criteria for quality"],
                    "relevance_indicators": ["indicators of relevance"],
                    "credibility_factors": ["factors for credibility"]
                },
                "expected_insights": [
                    {
                        "type": "insight type",
                        "description": "expected insight",
                        "value": "potential value"
                    }
                ]
            }
            """,
            input_variables=["query", "objective", "domain", "depth"]
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(
            query=context.query,
            objective=context.objective,
            domain=context.domain or "general",
            depth=context.required_depth
        )
        
        try:
            import json
            return json.loads(result)
        except:
            logger.error("Failed to parse video analysis strategy")
            return {
                "hypotheses": [],
                "key_aspects": [],
                "evaluation_criteria": {},
                "expected_insights": []
            }
    
    async def evaluate_content_credibility(
        self,
        metadata: VideoMetadata,
        segment: TranscriptSegment
    ) -> Dict[str, Any]:
        """Evaluate credibility of video content."""
        prompt = PromptTemplate(
            template="""
            Evaluate the credibility of this video segment:
            
            Video: {title}
            Channel: {channel}
            Category: {category}
            
            Segment Text:
            {text}
            
            Context: {context}
            
            Evaluate:
            1. Content accuracy and reliability
            2. Speaker expertise and authority
            3. Supporting evidence
            4. Potential biases
            
            Output as JSON:
            {
                "credibility_score": float,
                "accuracy_assessment": {
                    "score": float,
                    "factors": ["factors affecting accuracy"],
                    "concerns": ["potential concerns"]
                },
                "authority_assessment": {
                    "score": float,
                    "expertise_indicators": ["indicators of expertise"],
                    "credibility_factors": ["credibility factors"]
                },
                "evidence_assessment": {
                    "strength": "strong|moderate|weak",
                    "supporting_elements": ["supporting elements"],
                    "missing_elements": ["missing evidence"]
                },
                "bias_assessment": {
                    "detected_biases": ["detected biases"],
                    "impact": "high|medium|low",
                    "mitigation_suggestions": ["suggestions"]
                }
            }
            """,
            input_variables=["title", "channel", "category", "text", "context"]
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(
            title=metadata.title,
            channel=metadata.channel_name,
            category=metadata.category or "Unknown",
            text=segment.text,
            context=segment.context or "No context available"
        )
        
        try:
            import json
            return json.loads(result)
        except:
            logger.error("Failed to parse content credibility evaluation")
            return {
                "credibility_score": 0.5,
                "accuracy_assessment": {"score": 0.5}
            }
    
    async def extract_and_verify_claims(
        self,
        segments: List[TranscriptSegment],
        video_id: str
    ) -> List[ContentClaim]:
        """Extract and verify claims from video segments."""
        prompt = PromptTemplate(
            template="""
            Extract and verify claims from these video segments:
            
            {segments}
            
            For each segment:
            1. Identify key claims
            2. Assess evidence provided
            3. Check for consistency
            4. Evaluate confidence
            
            Output as JSON:
            {
                "claims": [
                    {
                        "statement": "claim statement",
                        "timestamp": float,
                        "supporting_evidence": ["supporting evidence"],
                        "contradicting_evidence": ["contradictions"],
                        "confidence_score": float,
                        "verification_status": "verified|disputed|unverified",
                        "context": ["relevant context"]
                    }
                ]
            }
            """,
            input_variables=["segments"]
        )
        
        # Process segments in batches
        claims = []
        batch_size = 5
        
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            segments_text = "\n\n".join([
                f"Segment at {s.start}s:\n{s.text}\nContext: {s.context}"
                for s in batch
            ])
            
            chain = LLMChain(llm=self.llm, prompt=prompt)
            result = await chain.arun(segments=segments_text)
            
            try:
                import json
                batch_results = json.loads(result)
                
                for claim_data in batch_results.get("claims", []):
                    claims.append(ContentClaim(
                        statement=claim_data["statement"],
                        video_id=video_id,
                        timestamp=claim_data["timestamp"],
                        confidence_score=claim_data["confidence_score"],
                        supporting_segments=[s for s in batch if s.start <= claim_data["timestamp"]],
                        verification_status=claim_data["verification_status"],
                        domain_context=claim_data["context"]
                    ))
            except:
                logger.error("Failed to parse claim extraction results")
        
        return claims
    
    async def synthesize_analysis(
        self,
        context: VideoContext,
        metadata: VideoMetadata,
        claims: List[ContentClaim]
    ) -> Dict[str, Any]:
        """Synthesize video analysis."""
        prompt = PromptTemplate(
            template="""
            Synthesize analysis for video:
            
            Title: {title}
            Query: {query}
            Objective: {objective}
            
            Based on:
            Channel: {channel}
            Category: {category}
            Claims: {claims}
            
            Generate:
            1. Key findings and insights
            2. Content gaps
            3. Recommendations
            4. Confidence assessment
            
            Output as JSON:
            {
                "key_findings": [
                    {
                        "finding": "main finding",
                        "supporting_claims": ["related claims"],
                        "confidence": float,
                        "implications": ["implications"]
                    }
                ],
                "content_gaps": [
                    {
                        "gap": "identified gap",
                        "impact": "high|medium|low",
                        "suggestions": ["suggestions to fill gap"]
                    }
                ],
                "recommendations": [
                    {
                        "recommendation": "specific recommendation",
                        "rationale": "reasoning",
                        "priority": "high|medium|low",
                        "next_steps": ["steps"]
                    }
                ],
                "confidence_assessment": {
                    "overall_score": float,
                    "strong_points": ["strong areas"],
                    "weak_points": ["weak areas"],
                    "reliability_factors": ["factors"]
                }
            }
            """,
            input_variables=["title", "query", "objective", "channel", "category", "claims"]
        )
        
        claims_text = "\n".join([
            f"- {c.statement} (confidence: {c.confidence_score})"
            for c in claims[:20]  # Limit to top 20 claims
        ])
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(
            title=metadata.title,
            query=context.query,
            objective=context.objective,
            channel=metadata.channel_name,
            category=metadata.category or "Unknown",
            claims=claims_text
        )
        
        try:
            import json
            return json.loads(result)
        except:
            logger.error("Failed to parse video analysis synthesis")
            return {
                "key_findings": [],
                "content_gaps": [],
                "recommendations": [],
                "confidence_assessment": {"overall_score": 0.5}
            }
