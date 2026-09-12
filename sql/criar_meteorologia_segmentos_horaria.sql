CREATE TABLE tcc.meteorologia_segmentos_horaria (

    id BIGSERIAL PRIMARY KEY,

    segmento_id TEXT NOT NULL,
    data_hora TIMESTAMP WITHOUT TIME ZONE NOT NULL,

    temperatura DOUBLE PRECISION,
    umidade DOUBLE PRECISION,
    precipitacao DOUBLE PRECISION,
    vento DOUBLE PRECISION,
    rajada DOUBLE PRECISION,

    temperatura_estacao VARCHAR(10),
    umidade_estacao VARCHAR(10),
    precipitacao_estacao VARCHAR(10),
    vento_estacao VARCHAR(10),
    rajada_estacao VARCHAR(10),

    temperatura_distancia_km DOUBLE PRECISION,
    umidade_distancia_km DOUBLE PRECISION,
    precipitacao_distancia_km DOUBLE PRECISION,
    vento_distancia_km DOUBLE PRECISION,
    rajada_distancia_km DOUBLE PRECISION,

    temperatura_ranking INTEGER,
    umidade_ranking INTEGER,
    precipitacao_ranking INTEGER,
    vento_ranking INTEGER,
    rajada_ranking INTEGER,

    CONSTRAINT uq_meteorologia_segmento_hora
        UNIQUE (segmento_id, data_hora),

    CONSTRAINT fk_meteorologia_segmento
        FOREIGN KEY (segmento_id)
        REFERENCES tcc.segmentos_rodovias(segmento_id)
);


CREATE INDEX idx_meteorologia_segmentos_horaria_segmento_hora
ON tcc.meteorologia_segmentos_horaria (
    segmento_id,
    data_hora
);


CREATE INDEX idx_meteorologia_segmentos_horaria_data_hora
ON tcc.meteorologia_segmentos_horaria (
    data_hora
);