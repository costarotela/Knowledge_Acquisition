-- Habilitar la extensión vector
DO $$ 
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
    RAISE NOTICE 'Vector extension created or already exists';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error creating vector extension: %', SQLERRM;
END $$;

-- Eliminar tablas si existen
DO $$ 
BEGIN
    DROP TABLE IF EXISTS relationships;
    DROP TABLE IF EXISTS citations;
    DROP TABLE IF EXISTS knowledge_items;
    DROP TABLE IF EXISTS videos;
    RAISE NOTICE 'Tables dropped successfully';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error dropping tables: %', SQLERRM;
END $$;

-- Crear tabla knowledge_items
DO $$ 
BEGIN
    CREATE TABLE IF NOT EXISTS knowledge_items (
        id BIGSERIAL PRIMARY KEY,
        source_url TEXT,
        concept TEXT,
        content TEXT,
        evidence_score REAL,
        novelty_score REAL,
        reference_list JSONB,
        embedding vector(384),
        category TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    RAISE NOTICE 'knowledge_items table created successfully';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error creating knowledge_items table: %', SQLERRM;
END $$;

-- Crear tabla citations
DO $$ 
BEGIN
    CREATE TABLE IF NOT EXISTS citations (
        id BIGSERIAL PRIMARY KEY,
        knowledge_id BIGINT REFERENCES knowledge_items(id),
        citation TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    RAISE NOTICE 'citations table created successfully';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error creating citations table: %', SQLERRM;
END $$;

-- Crear tabla relationships
DO $$ 
BEGIN
    CREATE TABLE IF NOT EXISTS relationships (
        id BIGSERIAL PRIMARY KEY,
        source_id BIGINT REFERENCES knowledge_items(id),
        target_id BIGINT REFERENCES knowledge_items(id),
        relationship_type TEXT,
        confidence_score REAL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    RAISE NOTICE 'relationships table created successfully';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error creating relationships table: %', SQLERRM;
END $$;

-- Crear tabla videos
DO $$ 
BEGIN
    CREATE TABLE IF NOT EXISTS videos (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        channel TEXT NOT NULL,
        url TEXT NOT NULL,
        transcript TEXT NOT NULL,
        embedding vector(384),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    RAISE NOTICE 'videos table created successfully';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error creating videos table: %', SQLERRM;
END $$;

-- Crear función para buscar videos similares
CREATE OR REPLACE FUNCTION match_videos(
    query_embedding vector(384),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id bigint,
    title text,
    channel text,
    url text,
    transcript text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id,
        v.title,
        v.channel,
        v.url,
        v.transcript,
        1 - (v.embedding <=> query_embedding) as similarity
    FROM videos v
    WHERE 1 - (v.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Verificar que las tablas existen
DO $$ 
BEGIN
    PERFORM * FROM knowledge_items LIMIT 1;
    PERFORM * FROM citations LIMIT 1;
    PERFORM * FROM relationships LIMIT 1;
    PERFORM * FROM videos LIMIT 1;
    RAISE NOTICE 'All tables exist and are accessible';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error verifying tables: %', SQLERRM;
END $$;
