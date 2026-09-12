-- ============================================================
-- TABELA DE AMOSTRAS NEGATIVAS
-- Horizonte de previsão: próximas 4 horas
--
-- Cada registro representa:
-- segmento + hora de referência
-- sem ocorrência de incêndio nas próximas 4 horas.
-- ============================================================

DROP TABLE IF EXISTS tcc.amostras_negativas_4h;

CREATE TABLE tcc.amostras_negativas_4h
(
    id BIGSERIAL PRIMARY KEY,

    segmento_id TEXT NOT NULL,
    rodovia TEXT NOT NULL,
    hora_referencia TIMESTAMP WITHOUT TIME ZONE NOT NULL,

    incendio_proximas_4h SMALLINT NOT NULL DEFAULT 0,

    criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_amostras_negativas_4h
        UNIQUE (segmento_id, hora_referencia),

    CONSTRAINT fk_amostras_negativas_segmento
        FOREIGN KEY (segmento_id)
        REFERENCES tcc.segmentos_rodovias(segmento_id),

    CONSTRAINT chk_amostras_negativas_alvo
        CHECK (incendio_proximas_4h = 0)
);


-- ============================================================
-- ÍNDICES
-- ============================================================

CREATE INDEX idx_amostras_negativas_4h_hora
ON tcc.amostras_negativas_4h(hora_referencia);


CREATE INDEX idx_amostras_negativas_4h_segmento_hora
ON tcc.amostras_negativas_4h(
    segmento_id,
    hora_referencia
);