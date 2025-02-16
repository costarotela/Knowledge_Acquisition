-- Habilitar la extensión vector
create extension if not exists vector;

-- Tabla de paquetes de viaje con embeddings
create table if not exists travel_packages (
    id uuid primary key default uuid_generate_v4(),
    data jsonb not null,
    embedding vector(1536),  -- Dimensión para OpenAI embeddings
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now())
);

-- Tabla de presupuestos
create table if not exists budgets (
    id uuid primary key default uuid_generate_v4(),
    data jsonb not null,
    status text not null default 'pending',
    metadata jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now())
);

-- Tabla de sesiones de venta
create table if not exists sales_sessions (
    id uuid primary key default uuid_generate_v4(),
    vendor_id text not null,
    customer_data jsonb,
    iterations jsonb[],
    status text not null default 'active',
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now())
);

-- Tabla de historial de precios
create table if not exists price_history (
    id uuid primary key default uuid_generate_v4(),
    package_id uuid references travel_packages(id),
    price numeric not null,
    timestamp timestamp with time zone default timezone('utc'::text, now())
);

-- Índices para búsqueda eficiente
create index if not exists travel_packages_embedding_idx on travel_packages 
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create index if not exists budgets_status_idx on budgets(status);
create index if not exists sales_sessions_status_idx on sales_sessions(status);
create index if not exists price_history_package_idx on price_history(package_id);

-- Función para actualizar el timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = timezone('utc'::text, now());
    return new;
end;
$$ language plpgsql;

-- Triggers para actualizar timestamps
create trigger update_travel_packages_updated_at
    before update on travel_packages
    for each row
    execute procedure update_updated_at_column();

create trigger update_budgets_updated_at
    before update on budgets
    for each row
    execute procedure update_updated_at_column();

create trigger update_sales_sessions_updated_at
    before update on sales_sessions
    for each row
    execute procedure update_updated_at_column();
