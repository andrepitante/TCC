DROP TABLE IF EXISTS tcc.incendios_segmentados;

CREATE TABLE tcc.incendios_segmentados (
    id BIGSERIAL PRIMARY KEY,

    id_incendio BIGINT NOT NULL,

    segmento_id TEXT NOT NULL,

    rodovia TEXT NOT NULL,

    km DOUBLE PRECISION,

    data_hora_inicio TIMESTAMP WITHOUT TIME ZONE,

    data DATE,

    municipio TEXT,

    latitude DOUBLE PRECISION,

    longitude DOUBLE PRECISION,

    geom geometry(Point, 4326),

    CONSTRAINT fk_incendios_segmentados_segmento
        FOREIGN KEY (segmento_id)
        REFERENCES tcc.segmentos_rodovias(segmento_id)
);


CREATE INDEX idx_incendios_segmentados_segmento
ON tcc.incendios_segmentados (segmento_id);


CREATE INDEX idx_incendios_segmentados_rodovia
ON tcc.incendios_segmentados (rodovia);


CREATE INDEX idx_incendios_segmentados_data
ON tcc.incendios_segmentados (data);


CREATE INDEX idx_incendios_segmentados_geom
ON tcc.incendios_segmentados
USING GIST (geom);