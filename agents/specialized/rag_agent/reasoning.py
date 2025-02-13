"""
Reasoning module for RAG agent.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

from .schemas import (
    ReasoningStep, ReasoningChain, CitationInfo,
    QueryContext, KnowledgeFragment, QueryType
)

logger = logging.getLogger(__name__)

class ReasoningEngine:
    """Engine for managing the reasoning process."""
    
    def __init__(self, llm: ChatOpenAI, config: Dict[str, Any]):
        self.llm = llm
        self.config = config
        self._setup_chains()
    
    def _setup_chains(self):
        """Setup reasoning chains."""
        # Chain for analyzing query type and context
        self.query_analyzer = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["query"],
                template="""
                Analyze the following query and determine:
                1. Query type (factual, analytical, exploratory, comparative, causal)
                2. Required depth of analysis (1-5)
                3. Domain context
                4. Temporal context if applicable
                
                Query: {query}
                """
            )
        )
        
        # Chain for generating reasoning steps
        self.step_generator = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["query", "context", "previous_steps", "knowledge"],
                template="""
                Given the query and context, generate the next reasoning step.
                Consider previous steps and available knowledge.
                
                Query: {query}
                Context: {context}
                Previous Steps: {previous_steps}
                Available Knowledge: {knowledge}
                """
            )
        )
        
        # Chain for evidence evaluation
        self.evidence_evaluator = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["evidence", "claim"],
                template="""
                Evaluate the evidence supporting this claim.
                Assign a confidence score and explain your reasoning.
                
                Claim: {claim}
                Evidence: {evidence}
                """
            )
        )
    
    async def generate_reasoning_chain(
        self,
        query: str,
        knowledge_fragments: List[KnowledgeFragment]
    ) -> ReasoningChain:
        """Generate a complete reasoning chain for a query."""
        start_time = datetime.now()
        
        # Analyze query
        query_analysis = await self.query_analyzer.arun(query=query)
        context = self._parse_query_analysis(query_analysis)
        
        # Initialize reasoning chain
        chain = ReasoningChain(
            query=query,
            context=context,
            steps=[],
            citations=[]
        )
        
        # Generate reasoning steps
        current_depth = 0
        while current_depth < context.required_depth:
            # Generate next step
            step = await self._generate_step(
                query,
                context,
                chain.steps,
                knowledge_fragments
            )
            
            # Evaluate evidence
            evidence_eval = await self._evaluate_evidence(
                step.intermediate_conclusion,
                knowledge_fragments
            )
            
            # Update step with evaluation
            step.confidence = evidence_eval["confidence"]
            step.evidence.extend(evidence_eval["supporting_evidence"])
            
            # Add citations
            chain.citations.extend([
                CitationInfo(
                    source_id=fragment.id,
                    source_type="knowledge_base",
                    content_snippet=fragment.content[:200],
                    relevance_score=fragment.confidence
                )
                for fragment in evidence_eval["supporting_evidence"]
            ])
            
            chain.steps.append(step)
            current_depth += 1
            
            # Check if we've reached a conclusion
            if evidence_eval["confidence"] > self.config.get("confidence_threshold", 0.8):
                break
        
        # Generate final conclusion
        chain.final_conclusion = self._generate_conclusion(chain.steps)
        chain.confidence_score = self._calculate_chain_confidence(chain.steps)
        chain.execution_time = (datetime.now() - start_time).total_seconds()
        
        return chain
    
    async def _generate_step(
        self,
        query: str,
        context: QueryContext,
        previous_steps: List[ReasoningStep],
        knowledge: List[KnowledgeFragment]
    ) -> ReasoningStep:
        """Generate a single reasoning step."""
        step_result = await self.step_generator.arun(
            query=query,
            context=context.dict(),
            previous_steps=[step.dict() for step in previous_steps],
            knowledge=[k.dict() for k in knowledge]
        )
        
        return self._parse_step_result(step_result, len(previous_steps) + 1)
    
    async def _evaluate_evidence(
        self,
        claim: str,
        knowledge: List[KnowledgeFragment]
    ) -> Dict[str, Any]:
        """Evaluate evidence for a claim."""
        eval_result = await self.evidence_evaluator.arun(
            claim=claim,
            evidence=[k.dict() for k in knowledge]
        )
        
        return self._parse_evidence_evaluation(eval_result)
    
    def _parse_query_analysis(self, analysis: str) -> QueryContext:
        """Parse query analysis into QueryContext."""
        try:
            # Extract information using regex patterns
            import re
            
            # Parse query type
            query_type_match = re.search(r"Query type:\s*(\w+)", analysis)
            query_type = query_type_match.group(1) if query_type_match else "factual"
            
            # Parse depth
            depth_match = re.search(r"Required depth:\s*(\d+)", analysis)
            depth = int(depth_match.group(1)) if depth_match else 3
            
            # Parse domain context
            domain_match = re.search(r"Domain context:\s*(.+?)(?=\n|$)", analysis)
            domain_context = [
                d.strip() 
                for d in domain_match.group(1).split(",")
            ] if domain_match else None
            
            # Parse temporal context
            temporal_match = re.search(r"Temporal context:\s*(.+?)(?=\n|$)", analysis)
            temporal_context = temporal_match.group(1) if temporal_match else None
            
            return QueryContext(
                query_type=QueryType(query_type.upper()),
                required_depth=depth,
                domain_context=domain_context,
                temporal_context=temporal_context
            )
            
        except Exception as e:
            logger.error(f"Error parsing query analysis: {str(e)}")
            # Return default context
            return QueryContext(
                query_type=QueryType.FACTUAL,
                required_depth=3
            )
    
    def _parse_step_result(self, result: str, step_number: int) -> ReasoningStep:
        """Parse step generation result into ReasoningStep."""
        try:
            # Extract information using regex patterns
            import re
            import json
            
            # Try to parse as JSON first
            try:
                data = json.loads(result)
                return ReasoningStep(
                    step_number=step_number,
                    description=data["description"],
                    evidence=data.get("evidence", []),
                    confidence=data.get("confidence", 0.7),
                    intermediate_conclusion=data.get("conclusion")
                )
            except json.JSONDecodeError:
                # Fallback to regex parsing
                description_match = re.search(r"Description:\s*(.+?)(?=\n|$)", result)
                conclusion_match = re.search(r"Conclusion:\s*(.+?)(?=\n|$)", result)
                confidence_match = re.search(r"Confidence:\s*(0\.\d+)", result)
                
                return ReasoningStep(
                    step_number=step_number,
                    description=description_match.group(1) if description_match else "Unknown step",
                    evidence=[],
                    confidence=float(confidence_match.group(1)) if confidence_match else 0.7,
                    intermediate_conclusion=conclusion_match.group(1) if conclusion_match else None
                )
                
        except Exception as e:
            logger.error(f"Error parsing step result: {str(e)}")
            # Return default step
            return ReasoningStep(
                step_number=step_number,
                description="Error parsing step",
                evidence=[],
                confidence=0.5,
                intermediate_conclusion=None
            )
    
    def _parse_evidence_evaluation(self, evaluation: str) -> Dict[str, Any]:
        """Parse evidence evaluation result."""
        try:
            import json
            
            # Try to parse as JSON first
            try:
                return json.loads(evaluation)
            except json.JSONDecodeError:
                # Parse using regex patterns
                import re
                
                # Extract confidence
                confidence_match = re.search(r"Confidence:\s*(0\.\d+)", evaluation)
                confidence = float(confidence_match.group(1)) if confidence_match else 0.7
                
                # Extract supporting evidence
                evidence_section = re.search(
                    r"Supporting Evidence:\s*(.+?)(?=\n\n|$)", 
                    evaluation, 
                    re.DOTALL
                )
                
                evidence = []
                if evidence_section:
                    evidence_items = re.finditer(
                        r"- (.+?)(?=\n-|\n\n|$)",
                        evidence_section.group(1),
                        re.DOTALL
                    )
                    evidence = [item.group(1).strip() for item in evidence_items]
                
                return {
                    "confidence": confidence,
                    "supporting_evidence": evidence
                }
                
        except Exception as e:
            logger.error(f"Error parsing evidence evaluation: {str(e)}")
            # Return default evaluation
            return {
                "confidence": 0.5,
                "supporting_evidence": []
            }
    
    def _generate_conclusion(self, steps: List[ReasoningStep]) -> str:
        """Generate final conclusion from reasoning steps."""
        if not steps:
            return "No conclusion could be reached."
        
        # Get the last step's conclusion
        final_step = steps[-1]
        if final_step.intermediate_conclusion:
            return final_step.intermediate_conclusion
        
        # If no conclusion in last step, synthesize from all steps
        conclusions = [
            step.intermediate_conclusion 
            for step in steps 
            if step.intermediate_conclusion
        ]
        
        if conclusions:
            return conclusions[-1]
        
        return "Unable to generate conclusion from reasoning steps."
    
    def _calculate_chain_confidence(self, steps: List[ReasoningStep]) -> float:
        """Calculate overall confidence of reasoning chain."""
        if not steps:
            return 0.0
        return sum(step.confidence for step in steps) / len(steps)
