-- Habilitar extensión vectorial
CREATE EXTENSION IF NOT EXISTS vector;

-- Tipos de contenido
CREATE TYPE content_type AS ENUM ('video', 'article', 'research', 'book');

-- Tabla principal de items de conocimiento
CREATE TABLE knowledge_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source JSONB NOT NULL,
    summary TEXT NOT NULL,
    main_topics TEXT[] NOT NULL,
    metadata JSONB DEFAULT '{}',
    quality_metrics JSONB DEFAULT '{}',
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE,
    content_type content_type NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Campos específicos para video
    video_metadata JSONB DEFAULT '{}'::jsonb CHECK (
        CASE WHEN content_type = 'video' 
        THEN video_metadata ? 'duration' 
             AND video_metadata ? 'frame_rate' 
             AND video_metadata ? 'resolution' 
             AND video_metadata ? 'codec'
        ELSE true
        END
    )
);

-- Tabla de fragmentos con soporte vectorial
CREATE TABLE knowledge_fragments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id UUID REFERENCES knowledge_items(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    start_time FLOAT,
    end_time FLOAT,
    keywords TEXT[],
    topics TEXT[],
    confidence_score FLOAT NOT NULL,
    embedding vector(384) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Campos para video
    frame_count INTEGER,
    scene_change BOOLEAN DEFAULT FALSE,
    visual_features JSONB DEFAULT '{}'::jsonb,
    frame_embeddings vector(512)[], -- Para embeddings de frames usando ViT o similar
    dominant_colors TEXT[],
    motion_intensity FLOAT -- Medida de movimiento en el segmento
);

-- Tabla de frames clave
CREATE TABLE video_frames (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fragment_id UUID REFERENCES knowledge_fragments(id) ON DELETE CASCADE,
    timestamp FLOAT NOT NULL,
    frame_path TEXT NOT NULL, -- Ruta al archivo del frame
    embedding vector(512) NOT NULL, -- Embedding visual
    objects_detected JSONB DEFAULT '{}',
    scene_score FLOAT, -- Qué tan representativo es de la escena
    visual_features JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de citaciones
CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id UUID REFERENCES knowledge_items(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    source_url TEXT NOT NULL,
    context TEXT,
    page_number INTEGER,
    timestamp FLOAT, -- Para videos
    frame_reference UUID REFERENCES video_frames(id), -- Referencia al frame
    accessed_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_fragments_item_id ON knowledge_fragments(item_id);
CREATE INDEX idx_citations_item_id ON citations(item_id);
CREATE INDEX idx_items_content_type ON knowledge_items(content_type);
CREATE INDEX idx_fragments_embedding ON knowledge_fragments USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_frames_embedding ON video_frames USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_fragments_time_range ON knowledge_fragments(start_time, end_time) 
    WHERE start_time IS NOT NULL AND end_time IS NOT NULL;
CREATE INDEX idx_frames_timestamp ON video_frames(timestamp);

-- Función para búsqueda vectorial multimodal
CREATE OR REPLACE FUNCTION match_knowledge_fragments(
    query_embedding vector(384),
    visual_query_embedding vector(512) DEFAULT NULL,
    match_threshold float,
    match_count int,
    filters jsonb DEFAULT '{}'
)
RETURNS TABLE (
    fragment_id UUID,
    item_id UUID,
    content TEXT,
    start_time FLOAT,
    end_time FLOAT,
    frame_path TEXT,
    similarity float,
    visual_similarity float
)
LANGUAGE plpgsql
AS $$
DECLARE
    time_range text;
    time_start float;
    time_end float;
BEGIN
    -- Extraer rango temporal si existe
    time_range := filters->>'time_range';
    IF time_range IS NOT NULL THEN
        time_start := (regexp_match(time_range, '^(\d+\.?\d*)'))[1]::float;
        time_end := (regexp_match(time_range, '-(\d+\.?\d*)$'))[1]::float;
    END IF;

    RETURN QUERY
    WITH frame_matches AS (
        SELECT 
            vf.fragment_id,
            vf.frame_path,
            CASE 
                WHEN visual_query_embedding IS NOT NULL 
                THEN 1 - (vf.embedding <=> visual_query_embedding)
                ELSE 0
            END as visual_sim
        FROM video_frames vf
        WHERE visual_query_embedding IS NOT NULL
        AND (1 - (vf.embedding <=> visual_query_embedding)) > match_threshold
    )
    SELECT DISTINCT ON (f.id)
        f.id as fragment_id,
        f.item_id,
        f.content,
        f.start_time,
        f.end_time,
        fm.frame_path,
        1 - (f.embedding <=> query_embedding) as similarity,
        fm.visual_sim as visual_similarity
    FROM knowledge_fragments f
    JOIN knowledge_items i ON f.item_id = i.id
    LEFT JOIN frame_matches fm ON f.id = fm.fragment_id
    WHERE (1 - (f.embedding <=> query_embedding)) > match_threshold
    AND CASE 
        WHEN filters->>'content_type' IS NOT NULL 
        THEN i.content_type = (filters->>'content_type')::content_type
        ELSE true
    END
    AND CASE 
        WHEN filters->>'min_confidence' IS NOT NULL 
        THEN f.confidence_score >= (filters->>'min_confidence')::float
        ELSE true
    END
    AND CASE
        WHEN time_range IS NOT NULL
        THEN f.start_time >= time_start AND f.end_time <= time_end
        ELSE true
    END
    ORDER BY 
        f.id,
        CASE 
            WHEN visual_query_embedding IS NOT NULL
            THEN (
                CASE 
                    WHEN fm.visual_sim IS NOT NULL THEN fm.visual_sim * 0.4  -- Peso para similitud visual
                    ELSE 0
                END
            )
            ELSE 0
        END +
        CASE 
            WHEN time_range IS NOT NULL AND i.content_type = 'video'
            THEN (
                CASE 
                    WHEN f.scene_change THEN 0.2  -- Bonus para cambios de escena
                    ELSE 0
                END
            )
            ELSE 0
        END + 
        (1 - (f.embedding <=> query_embedding)) * 0.6  -- Peso para similitud textual
        DESC
    LIMIT match_count;
END;
$$;
