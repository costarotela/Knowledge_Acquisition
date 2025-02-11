-- Crear extensión vector si no existe
create extension if not exists vector;

-- Eliminar objetos existentes
drop function if exists match_documents(vector(384), double precision, integer, text, double precision);
drop function if exists match_documents(vector(384), double precision, integer);
drop table if exists relationships;
drop table if exists citations;
drop table if exists knowledge_items;

-- Tabla de items de conocimiento
create table if not exists knowledge_items (
    id bigserial primary key,
    source_url text not null,
    concept text not null,
    content text not null,
    evidence_score double precision not null,
    novelty_score double precision not null,
    reference_list jsonb not null default '[]',
    embedding vector(384) not null,  -- Dimensión específica para all-MiniLM-L6-v2
    category text not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Tabla de citas
create table if not exists citations (
    id bigserial primary key,
    knowledge_id bigint references knowledge_items(id) on delete cascade,
    citation text not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Tabla de relaciones entre items
create table if not exists relationships (
    id bigserial primary key,
    source_id bigint references knowledge_items(id) on delete cascade,
    target_id bigint references knowledge_items(id) on delete cascade,
    similarity double precision not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    unique(source_id, target_id)
);

-- Crear índice para búsqueda vectorial
create index if not exists knowledge_items_embedding_idx
on knowledge_items
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

-- Función simple para encontrar documentos similares
create or replace function match_documents (
    query_embedding vector(384),
    similarity_threshold double precision,
    match_count integer
)
returns table (
    id bigint,
    content text,
    similarity double precision
)
language plpgsql
as $$
begin
    return query
    select
        ki.id,
        ki.content,
        1 - (ki.embedding <=> query_embedding) as similarity
    from knowledge_items ki
    where 1 - (ki.embedding <=> query_embedding) > similarity_threshold
    order by ki.embedding <=> query_embedding
    limit match_count;
end;
$$;

-- Función para encontrar relaciones entre conceptos
create or replace function get_concept_relationships(
    concept_name text,
    min_similarity double precision default 0.7,
    max_depth integer default 2
)
returns table (
    source_concept text,
    target_concept text,
    similarity double precision,
    source_content text,
    target_content text,
    depth integer
)
language plpgsql
as $$
begin
    return query
    with recursive concept_tree as (
        -- Base case: relaciones directas desde el concepto inicial
        select 
            k1.concept as source_concept,
            k2.concept as target_concept,
            r.similarity,
            k1.content as source_content,
            k2.content as target_content,
            1 as depth
        from knowledge_items k1
        join relationships r on k1.id = r.source_id
        join knowledge_items k2 on k2.id = r.target_id
        where k1.concept = concept_name
        and r.similarity >= min_similarity
        
        union
        
        -- Caso recursivo: encontrar relaciones adicionales
        select 
            ct.target_concept,
            k2.concept,
            r.similarity,
            ct.target_content,
            k2.content,
            ct.depth + 1
        from concept_tree ct
        join knowledge_items k1 on k1.concept = ct.target_concept
        join relationships r on k1.id = r.source_id
        join knowledge_items k2 on k2.id = r.target_id
        where ct.depth < max_depth
        and r.similarity >= min_similarity
    )
    select distinct 
        source_concept,
        target_concept,
        similarity,
        source_content,
        target_content,
        depth
    from concept_tree
    order by depth, similarity desc;
end;
$$;
