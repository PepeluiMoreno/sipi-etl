-- Tabla de datos masivos: SQL puro
CREATE TABLE IF NOT EXISTS osmwikidata.inmuebles (
    osm_id VARCHAR(50) PRIMARY KEY,
    name TEXT,
    inferred_type TEXT NOT NULL,
    denomination TEXT,
    diocese TEXT,
    operator TEXT,
    wikidata_qid VARCHAR(20),
    inception DATE,
    commons_category TEXT,
    heritage_status TEXT,
    historic TEXT,
    ruins BOOLEAN DEFAULT FALSE,
    geom GEOMETRY(Point, 4326),
    qa_flags JSONB,
    source_refs TEXT,
    address_street TEXT,
    address_city TEXT,
    address_postcode TEXT,
    run_id INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_osmwikidata_geom ON osmwikidata.inmuebles USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_osmwikidata_qid ON osmwikidata.inmuebles (wikidata_qid) WHERE wikidata_qid IS NOT NULL;

-- Tabla de auditoría
CREATE TABLE IF NOT EXISTS osmwikidata.pipeline_runs (
    run_id SERIAL PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    country VARCHAR(10) NOT NULL,
    status VARCHAR(20) CHECK (status IN (running, success, failed, no_changes)),
    records_extracted INTEGER,
    records_loaded INTEGER,
    execution_time_seconds INTEGER,
    diff_summary JSONB,
    error_message TEXT
);

CREATE INDEX idx_pipeline_runs_date ON osmwikidata.pipeline_runs (started_at DESC);
