DROP TABLE IF EXISTS tcc.segmentos_estacoes;

CREATE TABLE tcc.segmentos_estacoes (

    id BIGSERIAL PRIMARY KEY,

    segmento_id TEXT NOT NULL,

    codigo_estacao VARCHAR(10) NOT NULL,

    distancia_km DOUBLE PRECISION NOT NULL,

    ranking INTEGER NOT NULL,

    CONSTRAINT fk_segmentos_estacoes_segmento
        FOREIGN KEY (segmento_id)
        REFERENCES tcc.segmentos_rodovias(segmento_id),

    CONSTRAINT fk_segmentos_estacoes_estacao
        FOREIGN KEY (codigo_estacao)
        REFERENCES tcc.estacoes_meteorologicas(codigo_estacao),

    CONSTRAINT uq_segmento_estacao
        UNIQUE (segmento_id, codigo_estacao),

    CONSTRAINT uq_segmento_ranking
        UNIQUE (segmento_id, ranking),

    CONSTRAINT chk_distancia_positiva
        CHECK (distancia_km >= 0),

    CONSTRAINT chk_ranking_positivo
        CHECK (ranking >= 1)
);


CREATE INDEX idx_segmentos_estacoes_segmento
ON tcc.segmentos_estacoes (segmento_id);


CREATE INDEX idx_segmentos_estacoes_estacao
ON tcc.segmentos_estacoes (codigo_estacao);


CREATE INDEX idx_segmentos_estacoes_ranking
ON tcc.segmentos_estacoes (
    segmento_id,
    ranking
);