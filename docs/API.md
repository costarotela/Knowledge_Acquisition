# API Reference

## Core APIs

### YouTubeProcessor

```python
class YouTubeProcessor(AgentProcessor):
    """Procesador de videos de YouTube."""
    
    async def process(self, url: str, context: AgentContext) -> Dict[str, Any]:
        """
        Procesa un video de YouTube.
        
        Args:
            url: URL del video
            context: Contexto del agente
            
        Returns:
            Dict con información del video y transcripción
        """
```

### AgenticNutritionRAG

```python
class AgenticNutritionRAG(AgentModel):
    """Modelo RAG para nutrición."""
    
    async def process_video(self, title: str, channel: str, url: str, transcript: str) -> VideoKnowledge:
        """
        Procesa un video y extrae conocimiento estructurado.
        
        Args:
            title: Título del video
            channel: Canal del video
            url: URL del video
            transcript: Transcripción
            
        Returns:
            VideoKnowledge con el conocimiento estructurado
        """
    
    async def get_response(self, query: str, context: List[Dict]) -> RAGResponse:
        """
        Genera una respuesta usando el modelo.
        
        Args:
            query: Consulta del usuario
            context: Lista de documentos relevantes
            
        Returns:
            RAGResponse estructurada
        """
```

## Data Models

### VideoKnowledge

```python
class VideoKnowledge(BaseModel):
    """Conocimiento estructurado extraído de un video."""
    title: str
    channel: str
    url: str
    segments: List[VideoSegment]
    summary: str
    main_topics: List[str]
    metadata: Dict[str, Any]
    processed_at: datetime
```

### RAGResponse

```python
class RAGResponse(BaseModel):
    """Respuesta estructurada del sistema RAG."""
    answer: str
    sources: List[SearchResult]
    confidence: float
    reasoning: str
    follow_up: List[str]
```

## Database Schema

### Videos Table

```sql
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    channel TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    transcript TEXT NOT NULL,
    embedding VECTOR(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Video Segments Table

```sql
CREATE TABLE video_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID REFERENCES videos(id),
    content TEXT NOT NULL,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    embedding VECTOR(1536),
    keywords TEXT[],
    topics TEXT[],
    sentiment FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Endpoints

### Video Processing

```http
POST /api/videos/process
Content-Type: application/json

{
    "url": "https://youtube.com/watch?v=..."
}
```

### Query

```http
POST /api/query
Content-Type: application/json

{
    "query": "¿Qué son los cereales integrales?",
    "context": {
        "language": "es",
        "max_results": 3
    }
}
```

## Error Handling

Todos los endpoints retornan errores en el siguiente formato:

```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Descripción del error",
        "details": {
            "campo": "información adicional"
        }
    }
}
```

### Códigos de Error Comunes

- `VIDEO_NOT_FOUND`: Video no encontrado
- `INVALID_URL`: URL inválida
- `PROCESSING_ERROR`: Error procesando video
- `TRANSCRIPTION_ERROR`: Error obteniendo transcripción
- `QUERY_ERROR`: Error procesando consulta
- `DATABASE_ERROR`: Error de base de datos

## Rate Limiting

- Límite de 100 requests por hora por IP
- Límite de 10 videos procesados por hora por usuario
- Límite de 1000 consultas por día por usuario

## Autenticación

```http
POST /api/auth/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password"
}
```

Respuesta:

```json
{
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

## WebSocket Events

### Video Processing Progress

```javascript
socket.on('video_progress', (data) => {
    console.log(data.status, data.progress);
});
```

### Query Progress

```javascript
socket.on('query_progress', (data) => {
    console.log(data.status, data.context_found);
});
