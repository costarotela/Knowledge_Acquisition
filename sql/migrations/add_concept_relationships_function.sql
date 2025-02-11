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
            ct.target_concept as source_concept,
            k2.concept as target_concept,
            r.similarity,
            ct.target_content as source_content,
            k2.content as target_content,
            ct.depth + 1 as depth
        from concept_tree ct
        join knowledge_items k1 on k1.concept = ct.target_concept
        join relationships r on k1.id = r.source_id
        join knowledge_items k2 on k2.id = r.target_id
        where ct.depth < max_depth
        and r.similarity >= min_similarity
    )
    select distinct 
        ct.source_concept,
        ct.target_concept,
        ct.similarity,
        ct.source_content,
        ct.target_content,
        ct.depth
    from concept_tree ct
    order by ct.depth, ct.similarity desc;
end;
$$;
