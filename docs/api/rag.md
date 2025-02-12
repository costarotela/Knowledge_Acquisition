# RAG (Retrieval-Augmented Generation) API Reference

## Overview

The RAG API provides components for implementing Retrieval-Augmented Generation systems, combining vector search with language models for enhanced knowledge retrieval and generation.

## Core Components

### RAGSystem

```python
class RAGSystem:
    def __init__(self, config: RAGConfig):
        """
        Initialize RAG system.
        
        Args:
            config (RAGConfig): System configuration
        """
        pass

    async def query(self, question: str) -> RAGResponse:
        """
        Process a query through the RAG pipeline.
        
        Args:
            question (str): User question
            
        Returns:
            RAGResponse: Generated response with sources
        """
        pass

    async def add_knowledge(self, content: str, metadata: Dict[str, Any] = None):
        """
        Add new knowledge to the system.
        
        Args:
            content (str): Content to add
            metadata (Dict): Optional metadata
        """
        pass
```

### Retriever

```python
class Retriever:
    def __init__(self, vector_store: VectorStore):
        """
        Initialize retriever.
        
        Args:
            vector_store (VectorStore): Vector store for similarity search
        """
        pass

    async def retrieve(self, query: str, k: int = 5) -> List[Document]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query (str): Query string
            k (int): Number of documents to retrieve
            
        Returns:
            List[Document]: Retrieved documents
        """
        pass

    def rerank(self, query: str, documents: List[Document]) -> List[Document]:
        """
        Rerank retrieved documents by relevance.
        
        Args:
            query (str): Original query
            documents (List[Document]): Retrieved documents
            
        Returns:
            List[Document]: Reranked documents
        """
        pass
```

### Generator

```python
class Generator:
    def __init__(self, model: str = "gpt-4-turbo-preview"):
        """
        Initialize generator.
        
        Args:
            model (str): Language model to use
        """
        pass

    async def generate(self, 
                      query: str, 
                      context: List[str]) -> GeneratedResponse:
        """
        Generate response using retrieved context.
        
        Args:
            query (str): User query
            context (List[str]): Retrieved context
            
        Returns:
            GeneratedResponse: Generated response
        """
        pass

    def validate_response(self, 
                         response: str, 
                         context: List[str]) -> bool:
        """
        Validate generated response against context.
        
        Args:
            response (str): Generated response
            context (List[str]): Source context
            
        Returns:
            bool: True if response is valid
        """
        pass
```

## Data Classes

### RAGConfig

```python
@dataclass
class RAGConfig:
    retriever_k: int = 5
    max_tokens: int = 2000
    temperature: float = 0.7
    model: str = "gpt-4-turbo-preview"
    rerank_threshold: float = 0.7
```

### RAGResponse

```python
@dataclass
class RAGResponse:
    answer: str
    sources: List[Source]
    confidence: float
    metadata: Dict[str, Any]
```

### Source

```python
@dataclass
class Source:
    content: str
    relevance_score: float
    metadata: Dict[str, Any]
```

### GeneratedResponse

```python
@dataclass
class GeneratedResponse:
    text: str
    tokens_used: int
    finish_reason: str
    metadata: Dict[str, Any]
```

## Utility Functions

```python
def prepare_context(documents: List[Document], 
                   max_tokens: int) -> str:
    """
    Prepare retrieved documents as context.
    
    Args:
        documents (List[Document]): Retrieved documents
        max_tokens (int): Maximum context length
        
    Returns:
        str: Prepared context
    """
    pass

def evaluate_response(response: str, 
                     ground_truth: str) -> Dict[str, float]:
    """
    Evaluate response quality.
    
    Args:
        response (str): Generated response
        ground_truth (str): Ground truth answer
        
    Returns:
        Dict[str, float]: Evaluation metrics
    """
    pass

def extract_citations(response: str, 
                     sources: List[Source]) -> List[Citation]:
    """
    Extract source citations from response.
    
    Args:
        response (str): Generated response
        sources (List[Source]): Source documents
        
    Returns:
        List[Citation]: Extracted citations
    """
    pass
```

## Usage Examples

```python
# Initialize RAG system
config = RAGConfig(retriever_k=5, temperature=0.7)
rag = RAGSystem(config)

# Add knowledge
await rag.add_knowledge(
    content="Important information...",
    metadata={"source": "document1.pdf"}
)

# Query the system
response = await rag.query("What is the capital of France?")
print(f"Answer: {response.answer}")
print(f"Sources: {response.sources}")

# Direct retriever usage
retriever = Retriever(vector_store)
docs = await retriever.retrieve("query", k=5)
reranked_docs = retriever.rerank("query", docs)

# Direct generator usage
generator = Generator()
response = await generator.generate(
    query="What is ML?",
    context=["Machine learning is..."]
)
```

## Error Handling

```python
class RAGError(Exception):
    """Base class for RAG exceptions."""
    pass

class RetrievalError(RAGError):
    """Raised when document retrieval fails."""
    pass

class GenerationError(RAGError):
    """Raised when response generation fails."""
    pass

class ValidationError(RAGError):
    """Raised when response validation fails."""
    pass
```
