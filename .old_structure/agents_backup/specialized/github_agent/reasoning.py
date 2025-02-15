"""
Reasoning engine for GitHub Agent.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from langchain import PromptTemplate, LLMChain
from langchain.chat_models import ChatOpenAI

from .schemas import (
    RepoContext, CodeFragment, IssueInfo,
    CommitInfo, RepositoryKnowledge
)

logger = logging.getLogger(__name__)

class GitHubReasoning:
    """Reasoning engine for GitHub repository analysis."""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """Initialize reasoning engine."""
        self.llm = llm or ChatOpenAI(
            model_name="gpt-4",
            temperature=0
        )
    
    async def analyze_repository_context(
        self,
        context: RepoContext
    ) -> Dict[str, Any]:
        """Generate hypotheses about repository context."""
        prompt = PromptTemplate(
            template="""
            Analyze this GitHub repository context and generate hypotheses:
            
            Repository: {owner}/{name}
            Description: {description}
            Stars: {stars}
            Forks: {forks}
            Topics: {topics}
            Languages: {languages}
            
            Generate hypotheses about:
            1. Repository purpose and scope
            2. Development activity and community
            3. Code quality and maintenance
            4. Potential use cases
            
            Output as JSON:
            {
                "hypotheses": [
                    {
                        "type": "purpose|activity|quality|usage",
                        "statement": "hypothesis statement",
                        "confidence": float,
                        "evidence": ["supporting evidence"]
                    }
                ]
            }
            """,
            input_variables=["owner", "name", "description", "stars", "forks", "topics", "languages"]
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(
            owner=context.owner,
            name=context.name,
            description=context.description,
            stars=context.stars,
            forks=context.forks,
            topics=context.topics,
            languages=context.languages
        )
        
        try:
            import json
            return json.loads(result)
        except:
            logger.error("Failed to parse hypothesis generation result")
            return {"hypotheses": []}
    
    async def evaluate_code_quality(
        self,
        fragments: List[CodeFragment]
    ) -> Dict[str, Any]:
        """Evaluate code quality from fragments."""
        if not fragments:
            return {"quality_score": 0.0, "findings": []}
        
        prompt = PromptTemplate(
            template="""
            Evaluate the code quality of these file fragments:
            
            {fragments}
            
            Consider:
            1. Code organization and structure
            2. Documentation and readability
            3. Best practices adherence
            4. Potential issues or risks
            
            Output as JSON:
            {
                "quality_score": float,
                "findings": [
                    {
                        "type": "strength|weakness|risk",
                        "description": "finding description",
                        "evidence": "code evidence",
                        "impact": "high|medium|low"
                    }
                ]
            }
            """,
            input_variables=["fragments"]
        )
        
        fragments_text = "\n\n".join([
            f"File: {f.path}\nLanguage: {f.language}\nContent:\n{f.content[:500]}..."
            for f in fragments[:5]  # Limit analysis to top 5 files
        ])
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(fragments=fragments_text)
        
        try:
            import json
            return json.loads(result)
        except:
            logger.error("Failed to parse code quality evaluation")
            return {"quality_score": 0.0, "findings": []}
    
    async def analyze_development_patterns(
        self,
        commits: List[CommitInfo],
        issues: List[IssueInfo]
    ) -> Dict[str, Any]:
        """Analyze development patterns from commits and issues."""
        prompt = PromptTemplate(
            template="""
            Analyze development patterns from these commits and issues:
            
            Commits:
            {commits}
            
            Issues:
            {issues}
            
            Generate insights about:
            1. Development velocity and patterns
            2. Issue resolution and responsiveness
            3. Team collaboration patterns
            4. Project health indicators
            
            Output as JSON:
            {
                "patterns": [
                    {
                        "type": "velocity|collaboration|health",
                        "observation": "pattern description",
                        "evidence": ["supporting evidence"],
                        "significance": "high|medium|low"
                    }
                ],
                "health_score": float
            }
            """,
            input_variables=["commits", "issues"]
        )
        
        commits_text = "\n".join([
            f"- {c.date.date()}: {c.message}"
            for c in commits[:10]  # Recent commits
        ])
        
        issues_text = "\n".join([
            f"- #{i.number}: {i.title} ({i.state})"
            for i in issues[:10]  # Recent issues
        ])
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(
            commits=commits_text,
            issues=issues_text
        )
        
        try:
            import json
            return json.loads(result)
        except:
            logger.error("Failed to parse development pattern analysis")
            return {"patterns": [], "health_score": 0.0}
    
    async def synthesize_knowledge(
        self,
        context_analysis: Dict[str, Any],
        code_evaluation: Dict[str, Any],
        dev_patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize final knowledge from all analyses."""
        prompt = PromptTemplate(
            template="""
            Synthesize repository knowledge from these analyses:
            
            Context Analysis:
            {context_analysis}
            
            Code Evaluation:
            {code_evaluation}
            
            Development Patterns:
            {dev_patterns}
            
            Generate:
            1. Key findings and insights
            2. Recommendations
            3. Risk assessment
            4. Future predictions
            
            Output as JSON:
            {
                "insights": [
                    {
                        "category": "finding|recommendation|risk|prediction",
                        "content": "insight description",
                        "confidence": float,
                        "supporting_evidence": ["evidence"],
                        "action_items": ["suggested actions"]
                    }
                ],
                "overall_assessment": {
                    "quality_score": float,
                    "health_score": float,
                    "risk_level": "high|medium|low",
                    "recommendation_summary": "string"
                }
            }
            """,
            input_variables=["context_analysis", "code_evaluation", "dev_patterns"]
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(
            context_analysis=str(context_analysis),
            code_evaluation=str(code_evaluation),
            dev_patterns=str(dev_patterns)
        )
        
        try:
            import json
            return json.loads(result)
        except:
            logger.error("Failed to parse knowledge synthesis")
            return {
                "insights": [],
                "overall_assessment": {
                    "quality_score": 0.0,
                    "health_score": 0.0,
                    "risk_level": "medium",
                    "recommendation_summary": "Analysis failed"
                }
            }
