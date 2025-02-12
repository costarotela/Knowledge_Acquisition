# Examples

## Basic Usage Examples

### 1. Adding a Web Source

```python
from knowledge_acquisition import KnowledgeAgent

agent = KnowledgeAgent()

# Add a single URL
url = "https://example.com/article"
result = agent.add_source(url)
print(f"Added source: {result.source_id}")

# Add multiple URLs
urls = [
    "https://example.com/article1",
    "https://example.com/article2"
]
results = agent.add_sources(urls)
```

### 2. Processing Documents

```python
# Process a PDF document
with open("document.pdf", "rb") as f:
    result = agent.process_document(f, "pdf")
    
# Process a text file
with open("data.txt", "r") as f:
    result = agent.process_document(f, "text")
```

### 3. Querying Knowledge

```python
# Simple query
response = agent.query("What are the main topics in the processed documents?")

# Advanced query with filters
response = agent.query(
    "What are the key findings?",
    filters={
        "date_range": ["2024-01-01", "2024-02-01"],
        "confidence": 0.8
    }
)
```

## Advanced Examples

### 1. Custom Knowledge Processing

```python
from knowledge_acquisition import Processor, KnowledgeGraph

class CustomProcessor(Processor):
    def process(self, content):
        # Custom processing logic
        entities = self.extract_entities(content)
        relationships = self.find_relationships(entities)
        return KnowledgeGraph(entities, relationships)

# Use custom processor
agent = KnowledgeAgent(processor=CustomProcessor())
```

### 2. Batch Processing

```python
# Process multiple sources in batch
sources = [
    {"type": "url", "content": "https://example.com/1"},
    {"type": "file", "content": "document1.pdf"},
    {"type": "text", "content": "Some text content"}
]

results = agent.process_batch(
    sources,
    batch_size=10,
    max_workers=4
)
```

### 3. Knowledge Graph Navigation

```python
# Get related concepts
related = agent.find_related("artificial intelligence")

# Find paths between concepts
path = agent.find_path(
    start="machine learning",
    end="neural networks"
)

# Get concept clusters
clusters = agent.cluster_concepts(
    concept="data science",
    max_distance=2
)
```

### 4. Export and Integration

```python
# Export to different formats
agent.export_knowledge("output.json", format="json")
agent.export_knowledge("graph.gml", format="gml")

# Integration with other tools
neo4j_export = agent.to_neo4j(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)
```

### 5. Monitoring and Analytics

```python
# Get processing statistics
stats = agent.get_stats()

# Monitor specific source
source_status = agent.monitor_source("source_id")

# Get knowledge graph metrics
metrics = agent.graph_metrics()
```

## API Integration Examples

### 1. REST API Usage

```python
import requests

# Configuration
API_URL = "http://localhost:8000/api/v1"
API_KEY = "your-api-key"

# Add source
response = requests.post(
    f"{API_URL}/sources",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"url": "https://example.com/article"}
)

# Query knowledge
response = requests.post(
    f"{API_URL}/query",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"query": "What are the main topics?"}
)
```

### 2. Webhook Integration

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    
    # Process webhook data
    if data["event"] == "processing_complete":
        source_id = data["source_id"]
        status = data["status"]
        # Handle the event
        
    return {"status": "success"}
```
