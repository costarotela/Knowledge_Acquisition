"""
Pydantic schemas for RAG agent components.
"""
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator

class QueryType(str, Enum):
    """Types of queries that can be processed."""
    FACTUAL = "factual"
    ANALYTICAL = "analytical"
    EXPLORATORY = "exploratory"
    COMPARATIVE = "comparative"
    CAUSAL = "causal"

class ReasoningStep(BaseModel):
    """A single step in the reasoning process."""
    step_number: int
    description: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    intermediate_conclusion: Optional[str] = None

class CitationInfo(BaseModel):
    """Information about a citation."""
    source_id: str
    source_type: str
    content_snippet: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    context: Dict[str, Any] = Field(default_factory=dict)

class QueryContext(BaseModel):
    """Context information for a query."""
    query_type: QueryType
    required_depth: int = Field(ge=1, le=5)
    temporal_context: Optional[str] = None
    domain_context: Optional[List[str]] = None
    user_context: Optional[Dict[str, Any]] = None

class ReasoningChain(BaseModel):
    """Complete chain of reasoning."""
    query: str
    context: QueryContext
    steps: List[ReasoningStep] = Field(default_factory=list)
    citations: List[CitationInfo] = Field(default_factory=list)
    final_conclusion: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    execution_time: float
    timestamp: datetime = Field(default_factory=datetime.now)

    @validator("steps")
    def validate_steps_sequence(cls, v):
        """Validate that steps are in sequence."""
        if not v:
            return v
        step_numbers = [step.step_number for step in v]
        if step_numbers != list(range(1, len(v) + 1)):
            raise ValueError("Steps must be numbered sequentially")
        return v

class KnowledgeFragment(BaseModel):
    """A fragment of knowledge from the knowledge base."""
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

class GeneratedResponse(BaseModel):
    """Generated response with supporting evidence."""
    response_text: str
    reasoning_chain: ReasoningChain
    supporting_fragments: List[KnowledgeFragment]
    generated_knowledge: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentAction(BaseModel):
    """Action taken by the agent during reasoning."""
    action_type: str
    description: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class AgentState(BaseModel):
    """Current state of the agent."""
    current_task: Optional[str] = None
    reasoning_depth: int = 0
    explored_paths: List[str] = Field(default_factory=list)
    action_history: List[AgentAction] = Field(default_factory=list)
    working_memory: Dict[str, Any] = Field(default_factory=dict)
    
    def add_action(self, action: AgentAction):
        """Add an action to history."""
        self.action_history.append(action)
    
    def update_working_memory(self, key: str, value: Any):
        """Update working memory."""
        self.working_memory[key] = value
    
    def clear_working_memory(self):
        """Clear working memory."""
        self.working_memory.clear()
