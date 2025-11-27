-- ============================================================================
-- SCHEMA: matching
-- Matchings entre OSM y portales inmobiliarios
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS matching;

-- Tabla unificada de matchings
CREATE TABLE IF NOT EXISTS matching.osm_portals (
    id SERIAL PRIMARY KEY,
    
    -- OSM
    osm_type VARCHAR(20) NOT NULL,
    osm_id BIGINT NOT NULL,
    
    -- Portal (referencia a portals.inmuebles_raw)
    inmueble_id INTEGER NOT NULL REFERENCES portals.inmuebles_raw(id) ON DELETE CASCADE,
    
    -- Matching
    confidence_score NUMERIC(5, 2) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 100),
    match_method VARCHAR(50) NOT NULL,
    distance_meters NUMERIC(10, 2),
    
    -- Validación
    validated_by VARCHAR(50),
    validated_at TIMESTAMP,
    is_confirmed BOOLEAN DEFAULT FALSE,
    
    -- Metadatos
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    -- Constraints
    FOREIGN KEY (osm_type, osm_id) 
        REFERENCES osmwikidata.inmuebles(osm_type, osm_id) 
        ON DELETE CASCADE,
    
    -- Un inmueble solo puede matchear con un lugar OSM
    UNIQUE (inmueble_id),
    
    CONSTRAINT valid_match_method CHECK (
        match_method IN ('proximity', 'name_match', 'manual', 'hybrid')
    )
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_matching_osm 
    ON matching.osm_portals (osm_type, osm_id);

CREATE INDEX IF NOT EXISTS idx_matching_inmueble 
    ON matching.osm_portals (inmueble_id);

CREATE INDEX IF NOT EXISTS idx_matching_confidence 
    ON matching.osm_portals (confidence_score DESC);

-- Vista con datos del portal
CREATE OR REPLACE VIEW matching.matchings_completos AS
SELECT 
    m.*,
    i.portal,
    i.id_portal,
    i.titulo,
    i.url,
    i.precio,
    o.name as osm_name,
    o.lat as osm_lat,
    o.lon as osm_lon
FROM matching.osm_portals m
JOIN portals.inmuebles_raw i ON m.inmueble_id = i.id
JOIN osmwikidata.inmuebles o ON m.osm_type = o.osm_type AND m.osm_id = o.osm_id;