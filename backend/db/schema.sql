-- Proposed tables for Supabase (Postgres). Task T2 fills them; T3, T4, T5 and T9 read them.
-- The columns follow backend/app/schemas.py. Lists and nested records are jsonb,
-- to keep the first version small.

create table if not exists investigations (
  id                text primary key,
  source_id         text not null,
  title             text not null,
  acronym           text,
  summary           text,
  research_area     text,
  project_type      text,
  platform          text,
  environment       text,
  hardware          text,
  hardware_family   text,  -- not in the frontend shape yet; T4 and T5 use it
  safety_function   text,  -- prevention, detection or suppression; T4 uses it
  fuel_classes      jsonb not null default '[]',
  fuel_materials    jsonb not null default '[]',
  topic_tags        jsonb not null default '[]',
  measurement_types jsonb not null default '[]',
  conditions        jsonb not null default '[]',
  files             jsonb not null default '[]',
  publications      jsonb not null default '[]',
  source_url        text not null,
  doi               text,
  source_updated_at text,
  ingested_at       text not null,
  data_status       text not null check (data_status in ('sample', 'parsed', 'verified'))
);

create table if not exists tests (
  id               text primary key,
  investigation_id text not null references investigations (id),
  test_label       text,
  fuel             text,
  geometry         text,
  oxygen_pct       numeric,  -- % by volume
  pressure_kpa     numeric,
  flow_cm_s        numeric,
  diluent          text,
  outcome          text,
  source_file      text,
  source_row       integer,
  raw              jsonb not null default '{}',
  flags            jsonb not null default '[]',
  data_status      text not null check (data_status in ('sample', 'parsed', 'verified')),
  unique (investigation_id, source_file, source_row)
);

create index if not exists tests_investigation_id on tests (investigation_id);

create table if not exists habitats (
  id               text primary key,
  name             text not null,
  oxygen_pct_min   numeric,
  oxygen_pct_max   numeric,
  pressure_kpa_min numeric,
  pressure_kpa_max numeric,
  gravity          text,
  citation         jsonb not null,
  data_status      text not null check (data_status in ('sample', 'parsed', 'verified'))
);
