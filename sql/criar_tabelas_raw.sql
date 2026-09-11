-- ============================================================
-- TCC - Risco de Incêndios em Rodovias
-- Criação das tabelas de dados brutos (RAW)
-- ============================================================

-- ============================================================
-- 1. HISTÓRICO DE INCÊNDIOS
-- Fonte: base pública de focos de incêndio
-- ============================================================

CREATE TABLE IF NOT EXISTS tcc.incendios_raw
(
    id BIGSERIAL PRIMARY KEY,

    concessionaria TEXT,
    data_hora_inicio TIMESTAMP,
    data_hora_fim TIMESTAMP,
    numero_ocorrencia TEXT,

    rodovia TEXT,
    municipio TEXT,
    reg_adm_sp TEXT,

    km DOUBLE PRECISION,
    sentido TEXT,

    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    extensao TEXT,
    proporcao TEXT,
    local_origem TEXT,
    faixa_dominio TEXT,

    data_inicio DATE,
    id_hora TEXT,

    rodovia_km TEXT,
    rodovia_km_sentido TEXT,

    -- Ponto geográfico da ocorrência
    -- EPSG:4326 = WGS84
    geom geometry(Point, 4326)
);


-- ============================================================
-- 2. RODOVIAS OSM
-- Fonte: GeoJSON exportado do OpenStreetMap
-- ============================================================

CREATE TABLE IF NOT EXISTS tcc.rodovias_osm_raw
(
    id BIGSERIAL PRIMARY KEY,

    -- Identificador original do elemento OSM
    osm_id TEXT,

    -- Referência da rodovia
    -- Exemplos:
    -- SP-330
    -- SP-330;BR-050
    ref TEXT,

    nome TEXT,

    -- Tipo OSM da via
    -- motorway, trunk, motorway_link etc.
    highway TEXT,

    surface TEXT,
    maxspeed TEXT,
    lanes TEXT,
    oneway TEXT,

    bridge TEXT,
    carriageway_ref TEXT,

    -- Preserva todas as propriedades originais do GeoJSON
    atributos JSONB,

    -- Geometry em vez de LineString porque o arquivo possui
    -- LineString e MultiLineString
    geom geometry(Geometry, 4326)
);