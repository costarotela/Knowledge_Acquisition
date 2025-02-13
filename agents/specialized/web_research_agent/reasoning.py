"""
Reasoning engine for Web Research Agent.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from langchain import PromptTemplate, LLMChain
from langchain.chat_models import ChatOpenAI

from .schemas import (
    WebSource, ContentFragment, FactClaim,
    ResearchContext, ResearchFindings
)

logger = logging.getLogger(__name__)

class WebResearchReasoning:
    """Reasoning engine for web research."""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """Initialize reasoning engine."""
        self.llm = llm or ChatOpenAI(
            model_name="gpt-4",
            temperature=0
        )
    
    async def analyze_research_context(
        self,
        context: ResearchContext
    ) -> Dict[str, Any]:
        """Generate research strategy and hypotheses."""
        prompt = PromptTemplate(
            template="""
            Analyze this research context and generate a research strategy:
            
            Query: {query}
            Objective: {objective}
            Domain: {domain}
            Required Depth: {depth}
            
            Generate:
            1. Initial hypotheses to investigate
            2. Key questions to answer
            3. Potential research directions
            4. Source evaluation criteria
            
            Output as JSON:
            {
                "hypotheses": [
                    {
                        "statement": "hypothesis statement",
                        "rationale": "reasoning behind hypothesis",
                        "investigation_approach": ["steps to investigate"]
                    }
                ],
                "key_questions": [
                    {
                        "question": "specific question",
                        "importance": "high|medium|low",
                        "expected_insights": ["potential findings"]
                    }
                ],
                "research_directions": [
                    {
                        "path": "research direction",
                        "priority": "high|medium|low",
                        "required_sources": ["source types needed"]
                    }
                ],
                "source_criteria": {
                    "required_attributes": ["list of must-have attributes"],
                    "preferred_domains": ["list of preferred domains"],
                    "quality_indicators": ["list of quality indicators"]
                }
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
            logger.error("Failed to parse research strategy")
            return {
                "hypotheses": [],
                "key_questions": [],
                "research_directions": [],
                "source_criteria": {}
            }
    
    async def evaluate_source_credibility(
        self,
        source: WebSource,
        content: str
    ) -> Dict[str, Any]:
        """Evaluate credibility of a web source."""
        prompt = PromptTemplate(
            template="""
            Evaluate the credibility of this web source:
            
            URL: {url}
            Title: {title}
            Domain: {domain}
            Author: {author}
            Published Date: {date}
            
            Content Sample:
            {content}
            
            Evaluate:
            1. Source authority and reputation
            2. Content quality and accuracy
            3. Potential biases
            4. Verification status
            
            Output as JSON:
            {
                "credibility_score": float,
                "authority_score": float,
                "quality_score": float,
                "bias_assessment": {
                    "detected_biases": ["list of biases"],
                    "bias_impact": "high|medium|low"
                },
                "verification_status": {
                    "status": "verified|partially_verified|unverified",
                    "verification_sources": ["list of sources"],
                    "concerns": ["list of concerns"]
                },
                "recommendations": ["list of recommendations"]
            }
            """,
            input_variables=["url", "title", "domain", "author", "date", "content"]
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(
            url=str(source.url),
            title=source.title,
            domain=source.domain,
            author=source.author or "Unknown",
            date=source.published_date.isoformat() if source.published_date else "Unknown",
            content=content[:1000]  # Limit content size
        )
        
        try:
            import json
            return json.loads(result)
        except:
            logger.error("Failed to parse source credibility evaluation")
            return {
                "credibility_score": 0.5,
                "verification_status": {"status": "unverified"}
            }
    
    async def extract_and_verify_facts(
        self,
        fragments: List[ContentFragment]
    ) -> List[FactClaim]:
        """Extract and verify facts from content fragments."""
        prompt = PromptTemplate(
            template="""
            Extract and verify facts from these content fragments:
            
            {fragments}
            
            For each fact:
            1. Extract the core claim
            2. Identify supporting evidence
            3. Look for contradictions
            4. Assess confidence
            
            Output as JSON:
            {
                "facts": [
                    {
                        "statement": "fact statement",
                        "supporting_evidence": ["list of evidence"],
                        "contradicting_evidence": ["list of contradictions"],
                        "confidence_score": float,
                        "verification_status": "verified|disputed|unverified",
                        "source_quality": "high|medium|low"
                    }
                ]
            }
            """,
            input_variables=["fragments"]
        )
        
        # Process fragments in batches
        facts = []
        batch_size = 5
        
        for i in range(0, len(fragments), batch_size):
            batch = fragments[i:i + batch_size]
            fragments_text = "\n\n".join([
                f"Fragment from {f.source_url}:\n{f.content}\nContext: {f.context}"
                for f in batch
            ])
            
            chain = LLMChain(llm=self.llm, prompt=prompt)
            result = await chain.arun(fragments=fragments_text)
            
            try:
                import json
                batch_results = json.loads(result)
                
                for fact_data in batch_results.get("facts", []):
                    facts.append(FactClaim(
                        statement=fact_data["statement"],
                        source_urls=[f.source_url for f in batch],
                        confidence_score=fact_data["confidence_score"],
                        supporting_evidence=fact_data["supporting_evidence"],
                        contradicting_evidence=fact_data["contradicting_evidence"],
                        verification_status=fact_data["verification_status"]
                    ))
            except:
                logger.error("Failed to parse fact extraction results")
        
        return facts
    
    async def synthesize_findings(
        self,
        context: ResearchContext,
        sources: List[WebSource],
        facts: List[FactClaim]
    ) -> Dict[str, Any]:
        """Synthesize research findings."""
        prompt = PromptTemplate(
            template="""
            Synthesize research findings for:
            
            Query: {query}
            Objective: {objective}
            
            Based on:
            Sources: {sources}
            Verified Facts: {facts}
            
            Generate:
            1. Key findings and insights
            2. Knowledge gaps
            3. Recommendations
            4. Confidence assessment
            
            Output as JSON:
            {
                "key_findings": [
                    {
                        "finding": "main finding",
                        "supporting_facts": ["related facts"],
                        "confidence": float,
                        "implications": ["potential implications"]
                    }
                ],
                "knowledge_gaps": [
                    {
                        "gap": "identified gap",
                        "impact": "high|medium|low",
                        "research_suggestions": ["suggestions"]
                    }
                ],
                "recommendations": [
                    {
                        "recommendation": "specific recommendation",
                        "rationale": "reasoning",
                        "priority": "high|medium|low",
                        "implementation_steps": ["steps"]
                    }
                ],
                "confidence_assessment": {
                    "overall_score": float,
                    "strong_areas": ["areas with high confidence"],
                    "weak_areas": ["areas needing more research"]
                }
            }
            """,
            input_variables=["query", "objective", "sources", "facts"]
        )
        
        sources_text = "\n".join([
            f"- {s.title} ({s.domain}, trust_score: {s.trust_score})"
            for s in sources[:10]  # Limit to top 10 sources
        ])
        
        facts_text = "\n".join([
            f"- {f.statement} (confidence: {f.confidence_score})"
            for f in facts[:20]  # Limit to top 20 facts
        ])
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(
            query=context.query,
            objective=context.objective,
            sources=sources_text,
            facts=facts_text
        )
        
        try:
            import json
            return json.loads(result)
        except:
            logger.error("Failed to parse research synthesis")
            return {
                "key_findings": [],
                "knowledge_gaps": [],
                "recommendations": [],
                "confidence_assessment": {"overall_score": 0.5}
            }
