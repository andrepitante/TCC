DROP TABLE IF EXISTS tcc.features_incendios;

CREATE TABLE tcc.features_incendios
(
    id BIGSERIAL PRIMARY KEY,

    id_incendio BIGINT NOT NULL UNIQUE,

    segmento_id TEXT NOT NULL,
    rodovia TEXT NOT NULL,

    data_hora_inicio TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    hora_referencia TIMESTAMP WITHOUT TIME ZONE NOT NULL,

    -- ========================================================
    -- CONDIÇÕES METEOROLÓGICAS DA HORA
    -- ========================================================

    temperatura_atual DOUBLE PRECISION,
    umidade_atual DOUBLE PRECISION,
    precipitacao_atual DOUBLE PRECISION,
    vento_atual DOUBLE PRECISION,
    rajada_atual DOUBLE PRECISION,


    -- ========================================================
    -- JANELA DAS ÚLTIMAS 24 HORAS
    -- ========================================================

    temperatura_media_24h DOUBLE PRECISION,
    temperatura_max_24h DOUBLE PRECISION,

    umidade_media_24h DOUBLE PRECISION,
    umidade_min_24h DOUBLE PRECISION,

    vento_medio_24h DOUBLE PRECISION,
    rajada_max_24h DOUBLE PRECISION,

    chuva_24h DOUBLE PRECISION,

    -- Quantas horas das últimas 24 apresentaram precipitação > 0
    horas_com_chuva_24h INTEGER,


    -- ========================================================
    -- JANELA DAS ÚLTIMAS 72 HORAS
    -- ========================================================

    chuva_72h DOUBLE PRECISION,

    -- Quantas horas das últimas 72 apresentaram precipitação > 0
    horas_com_chuva_72h INTEGER,


    -- ========================================================
    -- JANELA DOS ÚLTIMOS 7 DIAS / 168 HORAS
    -- ========================================================

    chuva_168h DOUBLE PRECISION,

    -- Horas desde a última precipitação conhecida,
    -- limitado a no máximo 168 horas.
    horas_sem_chuva_ate_168h INTEGER,


    -- ========================================================
    -- QUALIDADE / COBERTURA DOS DADOS
    -- ========================================================

    horas_temp_24h INTEGER,
    horas_umidade_24h INTEGER,
    horas_vento_24h INTEGER,

    horas_chuva_24h INTEGER,
    horas_chuva_72h INTEGER,
    horas_chuva_168h INTEGER,


    -- ========================================================
    -- CLASSE
    -- ========================================================

    incendio SMALLINT NOT NULL DEFAULT 1,

    criado_em TIMESTAMP WITHOUT TIME ZONE
        DEFAULT CURRENT_TIMESTAMP,


    CONSTRAINT fk_features_incendio
        FOREIGN KEY (id_incendio)
        REFERENCES tcc.incendios_raw(id),

    CONSTRAINT fk_features_segmento
        FOREIGN KEY (segmento_id)
        REFERENCES tcc.segmentos_rodovias(segmento_id),

    CONSTRAINT chk_features_incendio
        CHECK (incendio IN (0, 1))
);


CREATE INDEX idx_features_incendios_segmento
ON tcc.features_incendios(segmento_id);


CREATE INDEX idx_features_incendios_hora
ON tcc.features_incendios(hora_referencia);