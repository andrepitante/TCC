-- ============================================================
-- TCC - Risco de Incêndios em Rodovias
-- Índices das tabelas RAW
-- ============================================================


-- ============================================================
-- INCÊNDIOS
-- ============================================================

-- Busca por rodovia
CREATE INDEX IF NOT EXISTS idx_incendios_raw_rodovia
ON tcc.incendios_raw (rodovia);


-- Busca temporal
CREATE INDEX IF NOT EXISTS idx_incendios_raw_data_inicio
ON tcc.incendios_raw (data_hora_inicio);


-- Consultas geográficas
CREATE INDEX IF NOT EXISTS idx_incendios_raw_geom
ON tcc.incendios_raw
USING GIST (geom);


-- ============================================================
-- RODOVIAS OSM
-- ============================================================

-- Busca pela referência da rodovia
CREATE INDEX IF NOT EXISTS idx_rodovias_osm_raw_ref
ON tcc.rodovias_osm_raw (ref);


-- Consultas espaciais
CREATE INDEX IF NOT EXISTS idx_rodovias_osm_raw_geom
ON tcc.rodovias_osm_raw
USING GIST (geom);