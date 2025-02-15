"""
RAG Agent implementation with agentic capabilities.
"""
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from langchain_community.chat_models import ChatOpenAI

from ...base_agents.knowledge_agent import KnowledgeAgent
from core_system.agent_orchestrator.base import Task, TaskResult
from .schemas import (
    QueryType, GeneratedResponse, AgentState,
    KnowledgeFragment
)
from .reasoning import ReasoningEngine
from .knowledge_manager import KnowledgeManager
from langchain import PromptTemplate, LLMChain

logger = logging.getLogger(__name__)

class RAGAgent(KnowledgeAgent):
    """Agent specialized in knowledge retrieval and generation."""
    
    def __init__(self, *args, **kwargs):
        """Initialize RAG agent."""
        super().__init__(*args, **kwargs)
        
        # Initialize components
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name=self.config.get("model_name", "gpt-4")
        )
        
        self.knowledge_manager = KnowledgeManager(self.config)
        self.reasoning_engine = ReasoningEngine(self.llm, self.config)
        
        # Initialize state
        self.state = AgentState()
    
    async def process_task(self, task: Task) -> TaskResult:
        """Process a task assigned to the agent."""
        try:
            self.state.current_task = task.task_id
            
            # Extract query from task
            query = task.data.get("query")
            if not query:
                return TaskResult(
                    success=False,
                    error="No query provided in task data"
                )
            
            # Generate response
            response = await self.generate_response(query)
            
            # Update task result
            result = TaskResult(
                success=True,
                data={
                    "response": response.response_text,
                    "reasoning": response.reasoning_chain.dict(),
                    "confidence": response.reasoning_chain.confidence_score
                }
            )
            
            # Store any new knowledge generated
            if response.generated_knowledge:
                await self._store_generated_knowledge(response.generated_knowledge)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing task: {str(e)}")
            return TaskResult(
                success=False,
                error=str(e)
            )
        
        finally:
            self.state.clear_working_memory()
    
    async def generate_response(self, query: str) -> GeneratedResponse:
        """Generate a response to a query."""
        # Retrieve relevant knowledge
        knowledge = await self.knowledge_manager.retrieve_knowledge(query)
        
        # Generate reasoning chain
        reasoning_chain = await self.reasoning_engine.generate_reasoning_chain(
            query,
            knowledge
        )
        
        # Generate final response
        response = await self._generate_final_response(
            query,
            reasoning_chain,
            knowledge
        )
        
        return response
    
    async def _generate_final_response(
        self,
        query: str,
        reasoning_chain: ReasoningChain,
        knowledge: List[KnowledgeFragment]
    ) -> GeneratedResponse:
        """Generate final response with supporting evidence."""
        response = GeneratedResponse(
            response_text=reasoning_chain.final_conclusion,
            reasoning_chain=reasoning_chain,
            supporting_fragments=knowledge
        )
        
        # Generate new knowledge if confidence is high
        if reasoning_chain.confidence_score > self.config.get("knowledge_generation_threshold", 0.8):
            new_knowledge = await self._generate_new_knowledge(
                query,
                reasoning_chain
            )
            response.generated_knowledge = new_knowledge
        
        return response
    
    async def _generate_new_knowledge(
        self,
        query: str,
        reasoning: ReasoningChain
    ) -> Dict[str, Any]:
        """Generate new knowledge from reasoning chain."""
        try:
            # Create generation prompt
            prompt = PromptTemplate(
                template="""
                Based on the reasoning chain, generate new knowledge that can be added to our knowledge base.
                Consider:
                1. Novel insights or patterns
                2. Relationships between concepts
                3. Generalizable principles
                4. Edge cases or exceptions
                
                Query: {query}
                Reasoning Steps:
                {steps}
                Final Conclusion: {conclusion}
                
                Output as JSON:
                {
                    "content": "new knowledge statement",
                    "type": "insight|relationship|principle|exception",
                    "confidence": float,
                    "metadata": {
                        "derived_from": "source information",
                        "requires_validation": bool,
                        "domain": "knowledge domain"
                    }
                }
                """,
                input_variables=["query", "steps", "conclusion"]
            )
            
            # Create generation chain
            chain = LLMChain(llm=self.llm, prompt=prompt)
            
            # Generate new knowledge
            result = await chain.arun(
                query=query,
                steps="\n".join([
                    f"{s.step_number}. {s.description} -> {s.intermediate_conclusion}"
                    for s in reasoning.steps
                ]),
                conclusion=reasoning.final_conclusion
            )
            
            # Parse result
            try:
                import json
                knowledge = json.loads(result)
                
                # Validate knowledge
                if not knowledge.get("content") or not knowledge.get("type"):
                    raise ValueError("Invalid knowledge format")
                
                # Add generation metadata
                knowledge["metadata"].update({
                    "generated_by": "rag_agent",
                    "generation_time": datetime.now().isoformat(),
                    "source_query": query,
                    "reasoning_confidence": reasoning.confidence_score
                })
                
                return knowledge
                
            except json.JSONDecodeError:
                logger.error("Failed to parse generated knowledge")
                return None
                
        except Exception as e:
            logger.error(f"Error generating new knowledge: {str(e)}")
            return None
    
    async def _store_generated_knowledge(
        self,
        knowledge: Dict[str, Any]
    ) -> bool:
        """Store newly generated knowledge."""
        try:
            fragment = KnowledgeFragment(
                id=f"generated_{datetime.now().timestamp()}",
                content=knowledge["content"],
                metadata={
                    "source": "rag_agent",
                    "generation_time": datetime.now().isoformat(),
                    **knowledge.get("metadata", {})
                },
                confidence=knowledge.get("confidence", 0.8)
            )
            
            if self.knowledge_manager.validate_fragment(fragment):
                return await self.knowledge_manager.store_knowledge([fragment])
            
            return False
            
        except Exception as e:
            logger.error(f"Error storing generated knowledge: {str(e)}")
            return False
