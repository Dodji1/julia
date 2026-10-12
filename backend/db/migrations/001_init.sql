-- Schéma initial de Julia : base documentaire et base vectorielle dans la même instance PostgreSQL,
-- séparées en tables (issue #6). Les documents viennent du manifeste, les chunks du contrat
-- LegalChunk (issue #12), les embeddings du modèle configuré (BGE-M3, 1024 dimensions).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Recherche plein texte en français, insensible aux accents (« impot » trouve « impôt »).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'french_unaccent') THEN
        CREATE TEXT SEARCH CONFIGURATION french_unaccent (COPY = french);
        ALTER TEXT SEARCH CONFIGURATION french_unaccent
            ALTER MAPPING FOR hword, hword_part, word WITH unaccent, french_stem;
    END IF;
END
$$;

CREATE TABLE documents (
    document_id     text PRIMARY KEY,
    title           text NOT NULL,
    domain          text NOT NULL,
    country         text NOT NULL,
    organization    text,
    document_type   text NOT NULL,
    source_level    smallint NOT NULL CHECK (source_level BETWEEN 1 AND 4),
    version_label   text,
    status          text NOT NULL CHECK (status IN ('en_vigueur', 'archive', 'a_verifier')),
    file_path       text,
    sha256          text,
    has_text_layer  boolean NOT NULL,
    in_mvp          boolean NOT NULL DEFAULT false,
    indexed_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE chunks (
    chunk_id     text PRIMARY KEY,
    document_id  text NOT NULL REFERENCES documents (document_id) ON DELETE CASCADE,
    ordinal      integer NOT NULL CHECK (ordinal >= 0),
    title        text,
    chapter      text,
    section      text,
    location     text,
    article      text,
    article_key  text,
    paragraph    text,
    page_start   integer CHECK (page_start >= 1),
    page_end     integer,
    content      text NOT NULL,
    content_tsv  tsvector GENERATED ALWAYS AS (to_tsvector('french_unaccent', content)) STORED,
    tags         text[] NOT NULL DEFAULT '{}',
    is_ocr       boolean NOT NULL DEFAULT false,
    UNIQUE (document_id, ordinal),
    CHECK (page_end >= page_start)
);

CREATE INDEX chunks_content_tsv_idx ON chunks USING gin (content_tsv);
CREATE INDEX chunks_tags_idx ON chunks USING gin (tags);
CREATE INDEX chunks_article_key_idx ON chunks (article_key);

CREATE TABLE chunk_embeddings (
    chunk_id   text NOT NULL REFERENCES chunks (chunk_id) ON DELETE CASCADE,
    model      text NOT NULL,
    embedding  vector(1024) NOT NULL,
    PRIMARY KEY (chunk_id, model)
);

CREATE INDEX chunk_embeddings_hnsw_idx ON chunk_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE TABLE corpus_versions (
    corpus_version   text PRIMARY KEY,
    embedding_model  text NOT NULL,
    documents        integer NOT NULL,
    chunks           integer NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- Une ligne par question : sert au débogage, à l'évaluation (étape 11) et au suivi pendant le congrès.
CREATE TABLE rag_traces (
    request_id     text PRIMARY KEY,
    created_at     timestamptz NOT NULL DEFAULT now(),
    question       text NOT NULL,
    filters        jsonb NOT NULL,
    status         text NOT NULL,
    retrieved      jsonb NOT NULL DEFAULT '[]',
    cited          text[] NOT NULL DEFAULT '{}',
    timings_ms     jsonb NOT NULL DEFAULT '{}',
    llm_model      text,
    input_tokens   integer,
    output_tokens  integer,
    error          text,
    client_hash    text
);

CREATE INDEX rag_traces_created_at_idx ON rag_traces (created_at);

CREATE TABLE feedback (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id  text NOT NULL,
    rating      smallint NOT NULL CHECK (rating IN (-1, 1)),
    comment     text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX feedback_request_id_idx ON feedback (request_id);
