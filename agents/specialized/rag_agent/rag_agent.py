"""
RAG Agent implementation with agentic capabilities.
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio
from datetime import datetime

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

from ...base_agents.knowledge_agent import KnowledgeAgent
from core_system.agent_orchestrator.base import Task, TaskResult
from .schemas import (
    QueryType, ReasoningStep, CitationInfo, QueryContext,
    ReasoningChain, KnowledgeFragment, GeneratedResponse,
    AgentAction, AgentState
)

logger = logging.getLogger(__name__)

class RAGAgent(KnowledgeAgent):
    """Agent specialized in knowledge retrieval and generation."""
    
    def __init__(self, *args, **kwargs):
        """Initialize RAG agent."""
        super().__init__(*args, **kwargs)
        
        # LLM settings
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name=self.config.get("model_name", "gpt-4")
        )
        
        # Vector store settings
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            persist_directory=self.config.get("vector_store_path")
        )
        
        # Retrieval settings
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": self.config.get("max_documents", 5)}
        )
        
        # Compression for better context
        self.compressor = LLMChainExtractor.from_llm(self.llm)
        self.compressed_retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor,
            base_retriever=self.retriever
        )
        
        # Chain settings
        self.reasoning_chain = self._create_reasoning_chain()
        self.generation_chain = self._create_generation_chain()
        
        # Agent state
        self.state = AgentState()
    
    async def _process_extraction(self, task: Task) -> TaskResult:
        """Process knowledge extraction from query."""
        try:
            query = task.input_data["query"]
            query_type = task.input_data.get("query_type", QueryType.FACTUAL)
            
            # Create query context
            context = QueryContext(
                query_type=query_type,
                required_depth=task.input_data.get("depth", 3),
                temporal_context=task.input_data.get("temporal_context"),
                domain_context=task.input_data.get("domain_context"),
                user_context=task.input_data.get("user_context")
            )
            
            # Execute reasoning chain
            start_time = datetime.now()
            reasoning_result = await self._execute_reasoning(query, context)
            
            if not reasoning_result:
                return TaskResult(
                    success=False,
                    error="Failed to execute reasoning chain"
                )
            
            # Generate response
            response = await self._generate_response(
                query,
                reasoning_result,
                context
            )
            
            if not response:
                return TaskResult(
                    success=False,
                    error="Failed to generate response"
                )
            
            # Store generated knowledge
            if response.generated_knowledge:
                success = await self._store_knowledge(
                    [response.generated_knowledge],
                    {"generated": 0.8}
                )
                
                if not success:
                    logger.warning("Failed to store generated knowledge")
            
            return TaskResult(
                success=True,
                data=response.dict(),
                metrics={
                    "reasoning_steps": len(reasoning_result.steps),
                    "citations_used": len(reasoning_result.citations),
                    "execution_time": (datetime.now() - start_time).total_seconds()
                }
            )
            
        except Exception as e:
            logger.error(f"Error in RAG extraction: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )
    
    async def _execute_reasoning(
        self,
        query: str,
        context: QueryContext
    ) -> Optional[ReasoningChain]:
        """Execute the reasoning chain."""
        try:
            # Initialize reasoning chain
            chain = ReasoningChain(
                query=query,
                context=context,
                execution_time=0
            )
            
            start_time = datetime.now()
            
            # Retrieve relevant documents
            docs = await self._retrieve_relevant_documents(query, context)
            
            # Execute reasoning steps
            current_step = 1
            current_conclusion = None
            
            while current_step <= context.required_depth:
                # Create reasoning step
                step = await self._execute_reasoning_step(
                    query,
                    current_conclusion,
                    docs,
                    current_step,
                    context
                )
                
                if not step:
                    break
                
                chain.steps.append(step)
                current_conclusion = step.intermediate_conclusion
                
                # Add citations
                for evidence in step.evidence:
                    citation = CitationInfo(
                        source_id=evidence["source_id"],
                        source_type=evidence["source_type"],
                        content_snippet=evidence["content"],
                        relevance_score=evidence["relevance"],
                        context=evidence.get("context", {})
                    )
                    chain.citations.append(citation)
                
                current_step += 1
            
            # Calculate final confidence
            chain.final_conclusion = current_conclusion
            chain.confidence_score = self._calculate_chain_confidence(chain)
            chain.execution_time = (datetime.now() - start_time).total_seconds()
            
            return chain
            
        except Exception as e:
            logger.error(f"Error executing reasoning: {e}")
            return None
    
    async def _retrieve_relevant_documents(
        self,
        query: str,
        context: QueryContext
    ) -> List[KnowledgeFragment]:
        """Retrieve relevant documents with compression."""
        try:
            # Record action
            self.state.add_action(AgentAction(
                action_type="retrieval",
                description="Retrieving relevant documents",
                inputs={"query": query, "context": context.dict()}
            ))
            
            # Get compressed documents
            docs = await self.compressed_retriever.aget_relevant_documents(query)
            
            # Convert to knowledge fragments
            fragments = []
            for doc in docs:
                fragment = KnowledgeFragment(
                    id=doc.metadata.get("id", "unknown"),
                    content=doc.page_content,
                    metadata=doc.metadata,
                    confidence=doc.metadata.get("confidence", 0.8)
                )
                fragments.append(fragment)
            
            return fragments
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
    
    async def _execute_reasoning_step(
        self,
        query: str,
        previous_conclusion: Optional[str],
        documents: List[KnowledgeFragment],
        step_number: int,
        context: QueryContext
    ) -> Optional[ReasoningStep]:
        """Execute a single reasoning step."""
        try:
            # Record action
            self.state.add_action(AgentAction(
                action_type="reasoning",
                description=f"Executing reasoning step {step_number}",
                inputs={
                    "query": query,
                    "previous_conclusion": previous_conclusion,
                    "documents": len(documents)
                }
            ))
            
            # Prepare evidence
            evidence = []
            for doc in documents:
                evidence.append({
                    "source_id": doc.id,
                    "source_type": doc.metadata.get("type", "unknown"),
                    "content": doc.content,
                    "relevance": self._calculate_relevance(doc, query)
                })
            
            # Execute reasoning chain
            result = await self.reasoning_chain.arun({
                "query": query,
                "previous_conclusion": previous_conclusion,
                "evidence": evidence,
                "step_number": step_number,
                "context": context.dict()
            })
            
            # Create reasoning step
            step = ReasoningStep(
                step_number=step_number,
                description=result["description"],
                evidence=evidence,
                confidence=result["confidence"],
                intermediate_conclusion=result["conclusion"]
            )
            
            return step
            
        except Exception as e:
            logger.error(f"Error executing reasoning step: {e}")
            return None
    
    async def _generate_response(
        self,
        query: str,
        reasoning: ReasoningChain,
        context: QueryContext
    ) -> Optional[GeneratedResponse]:
        """Generate final response with supporting evidence."""
        try:
            # Record action
            self.state.add_action(AgentAction(
                action_type="generation",
                description="Generating final response",
                inputs={
                    "query": query,
                    "reasoning_steps": len(reasoning.steps)
                }
            ))
            
            # Generate response
            result = await self.generation_chain.arun({
                "query": query,
                "reasoning_chain": reasoning.dict(),
                "context": context.dict()
            })
            
            # Get supporting fragments
            supporting_fragments = []
            for citation in reasoning.citations:
                fragment = KnowledgeFragment(
                    id=citation.source_id,
                    content=citation.content_snippet,
                    metadata=citation.context,
                    confidence=citation.relevance_score
                )
                supporting_fragments.append(fragment)
            
            # Create response
            response = GeneratedResponse(
                response_text=result["response"],
                reasoning_chain=reasoning,
                supporting_fragments=supporting_fragments,
                generated_knowledge=result.get("generated_knowledge"),
                metadata={
                    "model": self.llm.model_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None
    
    def _create_reasoning_chain(self) -> LLMChain:
        """Create the reasoning chain."""
        template = """
        Given the following context and evidence, reason about the query step by step.
        
        Query: {query}
        Previous Conclusion: {previous_conclusion}
        Step Number: {step_number}
        Context: {context}
        
        Evidence:
        {evidence}
        
        Provide:
        1. A description of this reasoning step
        2. A confidence score (0-1)
        3. An intermediate conclusion
        
        Output as JSON:
        {
            "description": "step description",
            "confidence": float,
            "conclusion": "intermediate conclusion"
        }
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=[
                "query", "previous_conclusion",
                "evidence", "step_number", "context"
            ]
        )
        
        return LLMChain(llm=self.llm, prompt=prompt)
    
    def _create_generation_chain(self) -> LLMChain:
        """Create the generation chain."""
        template = """
        Generate a comprehensive response based on the reasoning chain.
        
        Query: {query}
        Reasoning Chain: {reasoning_chain}
        Context: {context}
        
        Provide:
        1. A clear and concise response
        2. Any new knowledge generated during reasoning
        
        Output as JSON:
        {
            "response": "final response text",
            "generated_knowledge": {
                "type": "knowledge type",
                "content": "new knowledge",
                "confidence": float
            }
        }
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["query", "reasoning_chain", "context"]
        )
        
        return LLMChain(llm=self.llm, prompt=prompt)
    
    def _calculate_chain_confidence(self, chain: ReasoningChain) -> float:
        """Calculate overall confidence of reasoning chain."""
        if not chain.steps:
            return 0.0
        
        # Weight later steps more heavily
        total_weight = 0
        weighted_sum = 0
        
        for i, step in enumerate(chain.steps, 1):
            weight = i  # Linear weight increase
            total_weight += weight
            weighted_sum += step.confidence * weight
        
        return weighted_sum / total_weight
    
    def _calculate_relevance(
        self,
        fragment: KnowledgeFragment,
        query: str
    ) -> float:
        """Calculate relevance of a fragment to query."""
        try:
            # Simple cosine similarity if embeddings available
            if fragment.embedding and hasattr(self, 'query_embedding'):
                return self._cosine_similarity(
                    fragment.embedding,
                    self.query_embedding
                )
            
            # Fallback to metadata-based scoring
            score = 0.7  # Base score
            
            # Adjust based on metadata
            if fragment.metadata.get("type") == "direct_answer":
                score += 0.2
            elif fragment.metadata.get("type") == "related_context":
                score += 0.1
            
            # Confidence impact
            score *= fragment.confidence
            
            return min(1.0, score)
            
        except Exception:
            return 0.5
    
    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between vectors."""
        dot_product = sum(x * y for x, y in zip(v1, v2))
        norm1 = sum(x * x for x in v1) ** 0.5
        norm2 = sum(x * x for x in v2) ** 0.5
        return dot_product / (norm1 * norm2) if norm1 * norm2 != 0 else 0
