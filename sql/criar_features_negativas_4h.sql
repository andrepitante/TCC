-- ============================================================
-- FEATURES DAS AMOSTRAS NEGATIVAS
-- Horizonte de previsão: próximas 4 horas
--
-- Mesma estrutura meteorológica utilizada nas amostras
-- positivas, permitindo posteriormente unir as duas classes.
-- ============================================================

DROP TABLE IF EXISTS tcc.features_negativas_4h;

CREATE TABLE tcc.features_negativas_4h
(
    id BIGSERIAL PRIMARY KEY,

    segmento_id TEXT NOT NULL,
    rodovia TEXT NOT NULL,
    hora_referencia TIMESTAMP WITHOUT TIME ZONE NOT NULL,

    -- condições atuais
    temperatura_atual DOUBLE PRECISION,
    umidade_atual DOUBLE PRECISION,
    precipitacao_atual DOUBLE PRECISION,
    vento_atual DOUBLE PRECISION,
    rajada_atual DOUBLE PRECISION,

    -- últimas 24 horas
    temperatura_media_24h DOUBLE PRECISION,
    temperatura_max_24h DOUBLE PRECISION,
    umidade_media_24h DOUBLE PRECISION,
    umidade_min_24h DOUBLE PRECISION,
    vento_medio_24h DOUBLE PRECISION,
    rajada_max_24h DOUBLE PRECISION,

    chuva_24h DOUBLE PRECISION,
    horas_com_chuva_24h INTEGER,

    -- últimas 72 horas
    chuva_72h DOUBLE PRECISION,
    horas_com_chuva_72h INTEGER,

    -- últimos 7 dias
    chuva_168h DOUBLE PRECISION,
    horas_sem_chuva_ate_168h INTEGER,

    -- qualidade/cobertura dos dados
    horas_temp_24h INTEGER,
    horas_umidade_24h INTEGER,
    horas_vento_24h INTEGER,
    horas_chuva_24h INTEGER,
    horas_chuva_72h INTEGER,
    horas_chuva_168h INTEGER,

    incendio_proximas_4h SMALLINT NOT NULL DEFAULT 0,

    criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_features_negativas_4h
        UNIQUE (segmento_id, hora_referencia),

    CONSTRAINT fk_features_negativas_segmento
        FOREIGN KEY (segmento_id)
        REFERENCES tcc.segmentos_rodovias(segmento_id),

    CONSTRAINT chk_features_negativas_alvo
        CHECK (incendio_proximas_4h = 0)
);


CREATE INDEX idx_features_negativas_4h_hora
ON tcc.features_negativas_4h(hora_referencia);


CREATE INDEX idx_features_negativas_4h_segmento_hora
ON tcc.features_negativas_4h(
    segmento_id,
    hora_referencia
);