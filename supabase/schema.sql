-- RapidLocalSites schema
-- Run in Supabase SQL Editor (one-time).

create extension if not exists pgcrypto;

-- prospects: every business the pipeline has touched.
create table if not exists public.prospects (
    id uuid primary key default gen_random_uuid(),
    slug text unique not null,
    dedup_hash text unique not null,
    name text not null,
    city text,
    address text,
    category text,
    status text not null default 'new' check (status in (
        'new', 'rozpracovane', 'nepouzitelne', 'delivered',
        'contacted', 'signed', 'archived'
    )),
    source_url text,
    preview_url text,
    repo_url text,
    error_reason text,
    is_test boolean default false,
    raw_scrape jsonb,
    classification jsonb,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
create index if not exists prospects_status_idx on public.prospects(status);
create index if not exists prospects_created_at_idx on public.prospects(created_at);

-- customers: signed customers (FK into prospects).
create table if not exists public.customers (
    id uuid primary key default gen_random_uuid(),
    prospect_id uuid references public.prospects(id) on delete cascade,
    slug text unique not null,
    auth_user_id uuid,
    signed_at timestamptz default now(),
    domain text,
    notes text
);

-- content: editable site content (live-read by deployed site).
create table if not exists public.content (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid references public.customers(id) on delete cascade,
    slug text unique not null,
    data jsonb not null,
    updated_at timestamptz default now()
);

-- drafts: email drafts (fallback for Gmail MCP failure).
create table if not exists public.drafts (
    id uuid primary key default gen_random_uuid(),
    prospect_id uuid references public.prospects(id) on delete cascade,
    subject text,
    body text,
    to_email text,
    sent boolean default false,
    created_at timestamptz default now()
);

-- runs: log of each pipeline execution.
create table if not exists public.runs (
    id uuid primary key default gen_random_uuid(),
    batch_name text,
    started_at timestamptz default now(),
    finished_at timestamptz,
    processed_slugs text[],
    successes integer default 0,
    failures integer default 0,
    total_tokens integer,
    error_log jsonb,
    notes text
);

-- assets: per-customer photo URLs.
create table if not exists public.assets (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid references public.customers(id) on delete cascade,
    slug text not null,
    url text not null,
    alt text,
    type text check (type in ('before', 'after', 'gallery', 'interior', 'product', 'team')),
    sort_order integer default 0,
    created_at timestamptz default now()
);
create index if not exists assets_slug_idx on public.assets(slug);

-- Row-Level Security
alter table public.prospects enable row level security;
alter table public.customers enable row level security;
alter table public.content   enable row level security;
alter table public.drafts    enable row level security;
alter table public.runs      enable row level security;
alter table public.assets    enable row level security;

-- Service role bypasses RLS automatically. Below policies are for anon/authenticated.

-- Customers can read/update only their own content row.
drop policy if exists "content self read" on public.content;
create policy "content self read" on public.content
    for select
    using (
        customer_id in (
            select id from public.customers where auth_user_id = auth.uid()
        )
    );

drop policy if exists "content self update" on public.content;
create policy "content self update" on public.content
    for update
    using (
        customer_id in (
            select id from public.customers where auth_user_id = auth.uid()
        )
    );

-- Customers can read/write only their own assets.
drop policy if exists "assets self read" on public.assets;
create policy "assets self read" on public.assets
    for select
    using (
        customer_id in (
            select id from public.customers where auth_user_id = auth.uid()
        )
    );

drop policy if exists "assets self write" on public.assets;
create policy "assets self write" on public.assets
    for all
    using (
        customer_id in (
            select id from public.customers where auth_user_id = auth.uid()
        )
    )
    with check (
        customer_id in (
            select id from public.customers where auth_user_id = auth.uid()
        )
    );

-- Anon can read content for the live site (needed for live site to fetch without login).
-- If you want to restrict: create a signed JWT per site and check a `site_key` column.
drop policy if exists "content anon read" on public.content;
create policy "content anon read" on public.content
    for select
    to anon
    using (true);

drop policy if exists "assets anon read" on public.assets;
create policy "assets anon read" on public.assets
    for select
    to anon
    using (true);

-- prospects, drafts, runs: no anon/authenticated policies -> only service role can access.

-- Helper trigger: updated_at on prospects / content.
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists prospects_touch on public.prospects;
create trigger prospects_touch before update on public.prospects
    for each row execute function public.touch_updated_at();

drop trigger if exists content_touch on public.content;
create trigger content_touch before update on public.content
    for each row execute function public.touch_updated_at();
