DROP TABLE IF EXISTS tcc.estacoes_meteorologicas CASCADE;

CREATE TABLE tcc.estacoes_meteorologicas (

    codigo_estacao VARCHAR(10) PRIMARY KEY,

    nome TEXT NOT NULL,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    altitude DOUBLE PRECISION,

    situacao TEXT,

    data_inicial DATE,
    data_final DATE,

    periodicidade TEXT,

    arquivo_origem TEXT,

    geom geometry(Point, 4326),

    criado_em TIMESTAMP WITHOUT TIME ZONE
        DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- ÍNDICES
-- ============================================================

CREATE INDEX idx_estacoes_meteorologicas_geom
ON tcc.estacoes_meteorologicas
USING GIST (geom);


CREATE INDEX idx_estacoes_meteorologicas_situacao
ON tcc.estacoes_meteorologicas (situacao);