# Esquema de Base de Datos para Procesamiento de Video

Este documento describe la estructura de la base de datos utilizada para el almacenamiento y recuperación de conocimiento basado en video.

## Estructura General

El esquema está diseñado para soportar:
- Almacenamiento eficiente de videos y sus metadatos
- Búsqueda por similitud (texto y visual)
- Recuperación temporal precisa
- Trazabilidad del conocimiento

## Tablas Principales

### 1. video_knowledge_items
Almacena información principal sobre cada video procesado.

```sql
CREATE TABLE video_knowledge_items (
    id UUID PRIMARY KEY,
    knowledge_item_id BIGINT,      -- Referencia a knowledge_items general
    summary TEXT,                  -- Resumen del contenido
    main_topics TEXT[],           -- Temas principales
    metadata JSONB,               -- Metadatos flexibles
    quality_metrics JSONB,        -- Métricas de calidad
    processed_at TIMESTAMPTZ,     -- Fecha de procesamiento
    updated_at TIMESTAMPTZ,       -- Última actualización
    video_metadata JSONB,         -- Metadatos específicos de video
    created_at TIMESTAMPTZ        -- Fecha de creación
);
```

### 2. knowledge_fragments
Almacena fragmentos de video con análisis semántico y visual.

```sql
CREATE TABLE knowledge_fragments (
    id UUID PRIMARY KEY,
    video_item_id UUID,           -- Referencia al video
    content TEXT,                 -- Contenido textual
    start_time FLOAT,            -- Inicio del fragmento
    end_time FLOAT,              -- Fin del fragmento
    keywords TEXT[],             -- Palabras clave
    topics TEXT[],               -- Temas detectados
    confidence_score FLOAT,      -- Confianza del análisis
    embedding vector(384),       -- Embedding textual
    frame_count INTEGER,         -- Número de frames
    scene_change BOOLEAN,        -- Indicador de cambio de escena
    visual_features JSONB,       -- Características visuales
    frame_embeddings vector(512)[], -- Embeddings de frames
    dominant_colors TEXT[],      -- Colores dominantes
    motion_intensity FLOAT,      -- Intensidad de movimiento
    created_at TIMESTAMPTZ       -- Fecha de creación
);
```

### 3. video_frames
Almacena frames clave con análisis visual.

```sql
CREATE TABLE video_frames (
    id UUID PRIMARY KEY,
    fragment_id UUID,            -- Referencia al fragmento
    timestamp FLOAT,             -- Tiempo en el video
    frame_path TEXT,             -- Ruta al archivo
    embedding vector(512),       -- Embedding visual
    objects_detected JSONB,      -- Objetos detectados
    scene_score FLOAT,           -- Relevancia de la escena
    visual_features JSONB,       -- Características visuales
    created_at TIMESTAMPTZ       -- Fecha de creación
);
```

### 4. video_citations
Gestiona referencias a momentos específicos en videos.

```sql
CREATE TABLE video_citations (
    id UUID PRIMARY KEY,
    video_item_id UUID,          -- Referencia al video
    text TEXT,                   -- Texto de la cita
    source_url TEXT,             -- URL fuente
    context TEXT,                -- Contexto
    timestamp FLOAT,             -- Tiempo en el video
    frame_reference UUID,        -- Referencia al frame
    accessed_date TIMESTAMPTZ,   -- Fecha de acceso
    created_at TIMESTAMPTZ       -- Fecha de creación
);
```

## Índices

### Índices Vectoriales
```sql
-- Para búsqueda por similitud textual
CREATE INDEX idx_fragments_embedding 
ON knowledge_fragments USING ivfflat (embedding vector_cosine_ops);

-- Para búsqueda por similitud visual
CREATE INDEX idx_frames_embedding 
ON video_frames USING ivfflat (embedding vector_cosine_ops);
```

### Índices Temporales
```sql
-- Para búsqueda por rango temporal
CREATE INDEX idx_fragments_time_range 
ON knowledge_fragments(start_time, end_time) 
WHERE start_time IS NOT NULL AND end_time IS NOT NULL;

-- Para búsqueda por timestamp
CREATE INDEX idx_frames_timestamp 
ON video_frames(timestamp);
```

### Índices de Relaciones
```sql
CREATE INDEX idx_fragments_video_item_id ON knowledge_fragments(video_item_id);
CREATE INDEX idx_video_citations_item_id ON video_citations(video_item_id);
```

## Función de Búsqueda

La función `match_video_fragments` permite búsqueda multimodal:

```sql
match_video_fragments(
    query_embedding vector(384),          -- Embedding de texto
    visual_query_embedding vector(512),   -- Embedding visual
    match_threshold float DEFAULT 0.7,    -- Umbral de similitud
    match_count int DEFAULT 10           -- Número de resultados
)
```

### Características
- Búsqueda combinada de texto y visual
- Ponderación configurable (40% visual, 60% texto)
- Filtrado por umbral de similitud
- Límite de resultados configurable

## Uso con el Agente Inteligente

Este esquema permite al agente:
1. Almacenar y recuperar conocimiento de videos de forma eficiente
2. Realizar búsquedas semánticas en contenido textual y visual
3. Referenciar momentos específicos en videos
4. Mantener contexto y trazabilidad del conocimiento
5. Evaluar la calidad y relevancia del contenido

## Mantenimiento

Para mantener el rendimiento óptimo:
1. Monitorear el crecimiento de las tablas
2. Reindexar periódicamente los índices vectoriales
3. Vaciar regularmente los frames antiguos no referenciados
4. Mantener actualizadas las estadísticas de la base de datos
