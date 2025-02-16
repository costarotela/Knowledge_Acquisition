-- Función para buscar paquetes por similitud de embeddings
create or replace function match_travel_packages (
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  data jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    id,
    data,
    1 - (travel_packages.embedding <=> query_embedding) as similarity
  from travel_packages
  where 1 - (travel_packages.embedding <=> query_embedding) > match_threshold
  order by similarity desc
  limit match_count;
end;
$$;
