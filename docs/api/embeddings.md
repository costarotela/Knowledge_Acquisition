# Embeddings API Reference

## Overview

The Embeddings API provides functionality for generating, storing, and managing vector embeddings of text content.

## Core Components

### EmbeddingGenerator

```python
class EmbeddingGenerator:
    def __init__(self, model: str = "text-embedding-3-large"):
        """
        Initialize embedding generator.
        
        Args:
            model (str): Name of the embedding model to use
        """
        pass

    async def generate(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text (str): Input text
            
        Returns:
            np.ndarray: Vector embedding
        """
        pass

    async def generate_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts (List[str]): List of input texts
            
        Returns:
            np.ndarray: Matrix of embeddings
        """
        pass
```

### TextChunker

```python
class TextChunker:
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize text chunker.
        
        Args:
            chunk_size (int): Maximum chunk size in characters
            overlap (int): Overlap between chunks
        """
        pass

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text (str): Input text
            
        Returns:
            List[str]: List of text chunks
        """
        pass

    def chunk_document(self, document: Document) -> List[TextChunk]:
        """
        Split document into chunks with metadata.
        
        Args:
            document (Document): Input document
            
        Returns:
            List[TextChunk]: List of chunks with metadata
        """
        pass
```

## Storage Components

### VectorStore

```python
class VectorStore:
    def __init__(self, dimension: int, index_type: str = "HNSW"):
        """
        Initialize vector store.
        
        Args:
            dimension (int): Embedding dimension
            index_type (str): Type of index to use
        """
        pass

    async def add(self, id: str, vector: np.ndarray, metadata: Dict = None):
        """
        Add vector to store.
        
        Args:
            id (str): Unique identifier
            vector (np.ndarray): Vector embedding
            metadata (Dict): Optional metadata
        """
        pass

    async def search(self, query: np.ndarray, k: int = 10) -> List[SearchResult]:
        """
        Search for similar vectors.
        
        Args:
            query (np.ndarray): Query vector
            k (int): Number of results
            
        Returns:
            List[SearchResult]: Similar vectors with scores
        """
        pass

    def save(self, path: str):
        """
        Save index to disk.
        
        Args:
            path (str): Save path
        """
        pass

    @classmethod
    def load(cls, path: str) -> "VectorStore":
        """
        Load index from disk.
        
        Args:
            path (str): Load path
            
        Returns:
            VectorStore: Loaded vector store
        """
        pass
```

## Utility Classes

### SearchResult

```python
@dataclass
class SearchResult:
    id: str
    vector: np.ndarray
    score: float
    metadata: Dict[str, Any]
```

### TextChunk

```python
@dataclass
class TextChunk:
    text: str
    start_char: int
    end_char: int
    metadata: Dict[str, Any]
```

## Configuration

### EmbeddingConfig

```python
@dataclass
class EmbeddingConfig:
    model: str = "text-embedding-3-large"
    dimension: int = 1536
    batch_size: int = 32
    cache_dir: str = "./cache"
```

### VectorStoreConfig

```python
@dataclass
class VectorStoreConfig:
    dimension: int = 1536
    index_type: str = "HNSW"
    space: str = "cosine"
    ef_construction: int = 200
    M: int = 16
```

## Usage Examples

```python
# Generate embeddings
generator = EmbeddingGenerator()
embedding = await generator.generate("Example text")

# Chunk text
chunker = TextChunker(chunk_size=1000, overlap=200)
chunks = chunker.chunk_text(long_text)

# Store vectors
store = VectorStore(dimension=1536)
await store.add("doc1", embedding)

# Search vectors
results = await store.search(query_vector, k=10)

# Process document
doc_chunks = chunker.chunk_document(document)
embeddings = await generator.generate_batch([chunk.text for chunk in doc_chunks])
for chunk, emb in zip(doc_chunks, embeddings):
    await store.add(chunk.id, emb, chunk.metadata)
```
