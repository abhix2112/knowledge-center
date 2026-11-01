-- Applied on every app start. Every statement is idempotent (IF NOT EXISTS),
-- so running it twice is safe. Schema changes beyond adding tables will need
-- real migrations later (Alembic).

CREATE EXTENSION IF NOT EXISTS vector;  -- not used yet; needed for RAG

CREATE TABLE IF NOT EXISTS users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email         text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    full_name     text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS articles (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Human-friendly number shown as KB0001001, like ServiceNow.
    number          integer GENERATED ALWAYS AS IDENTITY (START WITH 1001) UNIQUE,
    title           text NOT NULL,
    body            text NOT NULL,
    category        text NOT NULL DEFAULT 'General',
    tags            text[] NOT NULL DEFAULT '{}',
    status          text NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'published', 'retired')),
    visibility      text NOT NULL DEFAULT 'public'
                    CHECK (visibility IN ('private', 'public')),
    source          text NOT NULL DEFAULT 'manual'
                    CHECK (source IN ('manual', 'upload', 'seed')),
    owner_id        uuid NOT NULL REFERENCES users (id),
    current_version integer NOT NULL DEFAULT 1,
    -- sha256 of title + body. Detects "nothing changed" edits now,
    -- and stale RAG chunks later.
    content_hash    text NOT NULL,
    published_at    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS articles_owner_idx ON articles (owner_id);
CREATE INDEX IF NOT EXISTS articles_status_visibility_idx ON articles (status, visibility);

-- One row per saved version of an article's title and body.
CREATE TABLE IF NOT EXISTS article_versions (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id   uuid NOT NULL REFERENCES articles (id) ON DELETE CASCADE,
    version      integer NOT NULL,
    title        text NOT NULL,
    body         text NOT NULL,
    content_hash text NOT NULL,
    created_by   uuid NOT NULL REFERENCES users (id),
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (article_id, version)
);

CREATE TABLE IF NOT EXISTS documents (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    filename     text NOT NULL,      -- original name, for display only
    storage_path text NOT NULL,      -- where the file is saved on disk
    content_type text NOT NULL,
    size_bytes   integer NOT NULL,
    uploaded_by  uuid NOT NULL REFERENCES users (id),
    article_id   uuid REFERENCES articles (id) ON DELETE SET NULL,
    created_at   timestamptz NOT NULL DEFAULT now()
);
