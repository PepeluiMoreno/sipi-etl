-- ============================================================================
-- SCHEMA: portals
-- Datos UNIFICADOS de TODOS los portales inmobiliarios
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS portals;

-- ============================================================================
-- Tabla unificada de inmuebles raw (TODOS los portales)
-- ============================================================================
CREATE TABLE IF NOT EXISTS portals.inmuebles_raw (
    -- Identificación
    id SERIAL PRIMARY KEY,
    portal VARCHAR(50) NOT NULL,           -- 'idealista', 'fotocasa', 'pisos_com', etc.
    id_portal VARCHAR(100) NOT NULL,        -- ID único en el portal origen
    url TEXT NOT NULL,
    
    -- Datos básicos
    titulo TEXT,
    descripcion TEXT,
    tipo VARCHAR(100),                      -- 'piso', 'casa', 'edificio', etc.
    
    -- Datos económicos
    precio NUMERIC(12, 2),
    superficie NUMERIC(10, 2),              -- m²
    
    -- Geolocalización (soporta múltiples niveles de precisión)
    geo_type VARCHAR(20) NOT NULL,          -- 'none', 'approximate', 'precise', 'polygon', 'address_only', 'postal_code'
    lat NUMERIC(10, 7),
    lon NUMERIC(10, 7),
    geom GEOMETRY(Point, 4326),
    uncertainty_radius_m INTEGER,           -- Para geo_type='approximate'
    polygon GEOMETRY(Polygon, 4326),        -- Para geo_type='polygon'
    
    -- Información textual de ubicación
    direccion TEXT,
    codigo_postal VARCHAR(10),
    barrio VARCHAR(200),
    distrito VARCHAR(200),
    ciudad VARCHAR(200),
    provincia VARCHAR(200),
    
    -- Metadata geográfica
    geo_source VARCHAR(50),                 -- 'google_maps', 'osm', 'schema_org', etc.
    geo_confidence NUMERIC(3, 2),           -- 0-1
    
    -- Características (flexible, cada portal puede tener diferentes)
    caracteristicas JSONB,                  -- Array de strings o estructura compleja
    imagenes JSONB,                         -- Array de URLs
    
    -- Datos específicos del portal (lo que no encaja en campos estándar)
    portal_specific_data JSONB,             -- Datos extras específicos del portal
    
    -- Metadatos de scraping
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scrape_source VARCHAR(50) DEFAULT 'selenium',
    
    -- Estado del anuncio
    is_active BOOLEAN DEFAULT TRUE,
    delisted_at TIMESTAMP,
    
    -- Constraints
    UNIQUE (portal, id_portal),             -- Un ID por portal es único
    CONSTRAINT positive_price CHECK (precio > 0 OR precio IS NULL),
    CONSTRAINT positive_surface CHECK (superficie IS NULL OR superficie > 0),
    CONSTRAINT valid_portal CHECK (
        portal IN ('idealista', 'fotocasa', 'pisos_com', 'habitaclia')
    ),
    CONSTRAINT valid_geo_type CHECK (
        geo_type IN ('none', 'approximate', 'precise', 'polygon', 'address_only', 'postal_code')
    ),
    CONSTRAINT geo_consistency CHECK (
        (geo_type = 'none') OR
        (geo_type IN ('approximate', 'precise') AND lat IS NOT NULL AND lon IS NOT NULL) OR
        (geo_type = 'polygon' AND polygon IS NOT NULL) OR
        (geo_type IN ('address_only', 'postal_code'))
    )
);

-- ============================================================================
-- Tabla unificada de detecciones (TODOS los portales)
-- ============================================================================
CREATE TABLE IF NOT EXISTS portals.detecciones (
    id SERIAL PRIMARY KEY,
    inmueble_id INTEGER NOT NULL REFERENCES portals.inmuebles_raw(id) ON DELETE CASCADE,
    
    -- Scoring
    score NUMERIC(5, 2) NOT NULL CHECK (score >= 0 AND score <= 100),
    status VARCHAR(50) NOT NULL,            -- 'en_seguimiento', 'detectado', 'confirmado', 'en_venta', 'vendido'
    evidences JSONB NOT NULL,               -- Array de strings con evidencias
    
    -- Matching con OSM
    osm_match_id BIGINT,
    osm_match_type VARCHAR(20),             -- 'node', 'way', 'relation'
    osm_match_confidence NUMERIC(5, 2),
    osm_match_method VARCHAR(50),           -- 'proximity', 'name_match', 'manual'
    
    -- Tracking temporal
    first_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    
    -- Tracking económico
    precio_inicial NUMERIC(12, 2),
    precio_actual NUMERIC(12, 2),
    precio_min_observado NUMERIC(12, 2),
    precio_max_observado NUMERIC(12, 2),
    num_cambios_precio INTEGER DEFAULT 0,
    
    CONSTRAINT valid_status CHECK (
        status IN ('en_seguimiento', 'detectado', 'confirmado', 'en_venta', 'vendido', 'retirado')
    ),
    CONSTRAINT osm_match_complete CHECK (
        (osm_match_id IS NULL AND osm_match_type IS NULL) OR
        (osm_match_id IS NOT NULL AND osm_match_type IS NOT NULL)
    )
);

-- ============================================================================
-- Tabla unificada de cambios/histórico (TODOS los portales)
-- ============================================================================
CREATE TABLE IF NOT EXISTS portals.cambios (
    id SERIAL PRIMARY KEY,
    inmueble_id INTEGER NOT NULL REFERENCES portals.inmuebles_raw(id) ON DELETE CASCADE,
    
    -- Tipo de cambio
    tipo_cambio VARCHAR(50) NOT NULL,
    
    -- Valores antes/después
    valor_anterior JSONB,
    valor_nuevo JSONB,
    
    -- Contexto
    descripcion TEXT,
    
    -- Temporal
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_tipo_cambio CHECK (
        tipo_cambio IN ('new', 'price_change', 'status_change', 'delisted', 'score_change', 'score_update')
    )
);

-- ============================================================================
-- Tabla de deduplicación cross-portal
-- ============================================================================
CREATE TABLE IF NOT EXISTS portals.duplicates (
    id SERIAL PRIMARY KEY,
    inmueble_1_id INTEGER NOT NULL REFERENCES portals.inmuebles_raw(id) ON DELETE CASCADE,
    inmueble_2_id INTEGER NOT NULL REFERENCES portals.inmuebles_raw(id) ON DELETE CASCADE,
    
    -- Confianza de que son el mismo inmueble
    confidence NUMERIC(5, 2) NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    
    -- Método de detección
    detection_method VARCHAR(50),           -- 'geo_proximity', 'address_match', 'manual'
    
    -- Metadata
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated BOOLEAN DEFAULT FALSE,
    validated_by VARCHAR(100),
    validated_at TIMESTAMP,
    
    notes TEXT,
    
    CONSTRAINT different_inmuebles CHECK (inmueble_1_id != inmueble_2_id),
    CONSTRAINT ordered_pair CHECK (inmueble_1_id < inmueble_2_id),
    UNIQUE (inmueble_1_id, inmueble_2_id)
);

-- ============================================================================
-- ÍNDICES
-- ============================================================================

-- Inmuebles Raw
CREATE INDEX IF NOT EXISTS idx_portals_raw_portal 
    ON portals.inmuebles_raw (portal);

CREATE INDEX IF NOT EXISTS idx_portals_raw_portal_id 
    ON portals.inmuebles_raw (portal, id_portal);

CREATE INDEX IF NOT EXISTS idx_portals_raw_geom 
    ON portals.inmuebles_raw USING GIST (geom) 
    WHERE geom IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_portals_raw_lat_lon 
    ON portals.inmuebles_raw (lat, lon) 
    WHERE lat IS NOT NULL AND lon IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_portals_raw_active 
    ON portals.inmuebles_raw (is_active, portal) 
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_portals_raw_precio 
    ON portals.inmuebles_raw (precio) 
    WHERE precio IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_portals_raw_ciudad 
    ON portals.inmuebles_raw (ciudad);

CREATE INDEX IF NOT EXISTS idx_portals_raw_provincia 
    ON portals.inmuebles_raw (provincia);

CREATE INDEX IF NOT EXISTS idx_portals_raw_scraped_at 
    ON portals.inmuebles_raw (scraped_at DESC);

-- Detecciones
CREATE INDEX IF NOT EXISTS idx_portals_detecciones_inmueble 
    ON portals.detecciones (inmueble_id);

CREATE INDEX IF NOT EXISTS idx_portals_detecciones_status 
    ON portals.detecciones (status);

CREATE INDEX IF NOT EXISTS idx_portals_detecciones_score 
    ON portals.detecciones (score DESC);

CREATE INDEX IF NOT EXISTS idx_portals_detecciones_osm_match 
    ON portals.detecciones (osm_match_type, osm_match_id) 
    WHERE osm_match_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_portals_detecciones_confirmed 
    ON portals.detecciones (confirmed_at DESC) 
    WHERE confirmed_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_portals_detecciones_first_detected 
    ON portals.detecciones (first_detected_at DESC);

-- Cambios
CREATE INDEX IF NOT EXISTS idx_portals_cambios_inmueble 
    ON portals.cambios (inmueble_id);

CREATE INDEX IF NOT EXISTS idx_portals_cambios_tipo 
    ON portals.cambios (tipo_cambio);

CREATE INDEX IF NOT EXISTS idx_portals_cambios_detected_at 
    ON portals.cambios (detected_at DESC);

-- Duplicates
CREATE INDEX IF NOT EXISTS idx_portals_duplicates_inmueble_1 
    ON portals.duplicates (inmueble_1_id);

CREATE INDEX IF NOT EXISTS idx_portals_duplicates_inmueble_2 
    ON portals.duplicates (inmueble_2_id);

CREATE INDEX IF NOT EXISTS idx_portals_duplicates_confidence 
    ON portals.duplicates (confidence DESC);

CREATE INDEX IF NOT EXISTS idx_portals_duplicates_unvalidated 
    ON portals.duplicates (detected_at DESC) 
    WHERE validated = FALSE;

-- ============================================================================
-- COMENTARIOS
-- ============================================================================

COMMENT ON SCHEMA portals IS 'Datos unificados de TODOS los portales inmobiliarios';

COMMENT ON TABLE portals.inmuebles_raw IS 'Todos los inmuebles scrapeados de todos los portales';
COMMENT ON COLUMN portals.inmuebles_raw.portal IS 'Portal origen: idealista, fotocasa, pisos_com, habitaclia, etc.';
COMMENT ON COLUMN portals.inmuebles_raw.id_portal IS 'ID único del inmueble en el portal origen';
COMMENT ON COLUMN portals.inmuebles_raw.geo_type IS 'Tipo de geolocalización: none, approximate, precise, polygon, address_only, postal_code';
COMMENT ON COLUMN portals.inmuebles_raw.portal_specific_data IS 'Datos específicos del portal que no encajan en campos estándar';

COMMENT ON TABLE portals.detecciones IS 'Detecciones de inmuebles religiosos de todos los portales';
COMMENT ON TABLE portals.cambios IS 'Histórico de cambios de inmuebles de todos los portales';
COMMENT ON TABLE portals.duplicates IS 'Deduplicación: mismo inmueble anunciado en múltiples portales';

-- ============================================================================
-- VISTAS ÚTILES
-- ============================================================================

-- Vista de detecciones con datos del inmueble
CREATE OR REPLACE VIEW portals.detecciones_completas AS
SELECT 
    d.*,
    i.portal,
    i.id_portal,
    i.titulo,
    i.url,
    i.precio,
    i.superficie,
    i.lat,
    i.lon,
    i.ciudad,
    i.provincia,
    i.is_active
FROM portals.detecciones d
JOIN portals.inmuebles_raw i ON d.inmueble_id = i.id;

-- Vista de inmuebles activos por portal
CREATE OR REPLACE VIEW portals.stats_por_portal AS
SELECT 
    portal,
    COUNT(*) as total_inmuebles,
    COUNT(*) FILTER (WHERE is_active) as activos,
    COUNT(*) FILTER (WHERE NOT is_active) as inactivos,
    AVG(precio) FILTER (WHERE precio IS NOT NULL) as precio_medio,
    MIN(scraped_at) as primer_scraping,
    MAX(scraped_at) as ultimo_scraping
FROM portals.inmuebles_raw
GROUP BY portal;

-- Vista de detecciones por portal
CREATE OR REPLACE VIEW portals.detecciones_por_portal AS
SELECT 
    i.portal,
    d.status,
    COUNT(*) as total,
    AVG(d.score) as score_medio,
    COUNT(*) FILTER (WHERE d.osm_match_id IS NOT NULL) as con_match_osm
FROM portals.detecciones d
JOIN portals.inmuebles_raw i ON d.inmueble_id = i.id
GROUP BY i.portal, d.status;