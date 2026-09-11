DROP TABLE IF EXISTS tcc.segmentos_posicao;

CREATE TABLE tcc.segmentos_posicao (
    id BIGSERIAL PRIMARY KEY,

    segmento_id TEXT NOT NULL UNIQUE,

    rodovia TEXT NOT NULL,

    qtd_pontos INTEGER NOT NULL DEFAULT 0,

    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    metodo TEXT NOT NULL,

    geom geometry(Point, 4326),

    CONSTRAINT fk_segmentos_posicao_segmento
        FOREIGN KEY (segmento_id)
        REFERENCES tcc.segmentos_rodovias(segmento_id)
);

CREATE INDEX idx_segmentos_posicao_segmento
ON tcc.segmentos_posicao (segmento_id);

CREATE INDEX idx_segmentos_posicao_rodovia
ON tcc.segmentos_posicao (rodovia);

CREATE INDEX idx_segmentos_posicao_geom
ON tcc.segmentos_posicao
USING GIST (geom);