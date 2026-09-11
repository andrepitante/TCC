DROP TABLE IF EXISTS tcc.segmentos_rodovias;

CREATE TABLE tcc.segmentos_rodovias (
    id BIGSERIAL PRIMARY KEY,

    segmento_id TEXT NOT NULL UNIQUE,

    rodovia TEXT NOT NULL,

    numero_segmento INTEGER NOT NULL,

    km_inicio DOUBLE PRECISION NOT NULL,

    km_fim DOUBLE PRECISION NOT NULL,

    CONSTRAINT chk_segmento_km
        CHECK (km_fim > km_inicio)
);


CREATE INDEX idx_segmentos_rodovias_rodovia
ON tcc.segmentos_rodovias (rodovia);


CREATE INDEX idx_segmentos_rodovias_km
ON tcc.segmentos_rodovias (
    rodovia,
    km_inicio,
    km_fim
);