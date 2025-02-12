# Configuration Guide

## Environment Variables

### Required Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4-turbo-preview

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/knowledge_db
VECTOR_STORE_PATH=./vector_store

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
```

### Optional Variables

```bash
# Performance Tuning
BATCH_SIZE=100
MAX_WORKERS=4
CACHE_TTL=3600

# Feature Flags
ENABLE_MONITORING=true
ENABLE_RATE_LIMITING=true
```

## Database Configuration

### PostgreSQL Setup

1. Create database:
```sql
CREATE DATABASE knowledge_db;
```

2. Initialize tables:
```bash
python scripts/init_db.py
```

3. Configure connection:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/knowledge_db
```

## Vector Store Configuration

### Local Vector Store

```bash
VECTOR_STORE_PATH=./vector_store
VECTOR_DIMENSION=1536
INDEX_TYPE=HNSW
```

### Cloud Vector Store

```bash
VECTOR_STORE_TYPE=pinecone
PINECONE_API_KEY=your-key
PINECONE_ENV=production
```

## Scraping Configuration

### Web Scraping

```bash
MAX_DEPTH=3
RESPECT_ROBOTS_TXT=true
REQUEST_DELAY=1.0
```

### Rate Limiting

```bash
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
```

## Monitoring Configuration

### Logging

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=./logs/app.log
```

### Metrics

```bash
ENABLE_METRICS=true
METRICS_PORT=9090
```

## Security Configuration

### API Security

```bash
API_KEY_REQUIRED=true
JWT_SECRET=your-secret
TOKEN_EXPIRY=3600
```

### CORS Settings

```bash
ALLOWED_ORIGINS=["http://localhost:3000"]
ALLOWED_METHODS=["GET", "POST"]
```

## Cache Configuration

### Redis Cache

```bash
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600
```

### Local Cache

```bash
CACHE_TYPE=local
CACHE_SIZE=1000
```

## Advanced Configuration

### LLM Settings

```bash
MODEL_TEMPERATURE=0.7
MAX_TOKENS=2000
TOP_P=0.95
```

### Embedding Settings

```bash
EMBEDDING_MODEL=text-embedding-3-large
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```
