DROP TABLE IF EXISTS tcc.amostras_positivas_4h;

CREATE TABLE tcc.amostras_positivas_4h
(
    id BIGSERIAL PRIMARY KEY,

    segmento_id TEXT NOT NULL,
    rodovia TEXT NOT NULL,

    hora_referencia TIMESTAMP WITHOUT TIME ZONE NOT NULL,

    primeira_ocorrencia TIMESTAMP WITHOUT TIME ZONE NOT NULL,

    minutos_ate_incendio INTEGER NOT NULL,

    qtd_incendios_janela INTEGER NOT NULL DEFAULT 1,

    incendio_proximas_4h SMALLINT NOT NULL DEFAULT 1,

    criado_em TIMESTAMP WITHOUT TIME ZONE
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_amostra_segmento
        FOREIGN KEY (segmento_id)
        REFERENCES tcc.segmentos_rodovias(segmento_id),

    CONSTRAINT uq_amostra_positiva_4h
        UNIQUE (segmento_id, hora_referencia),

    CONSTRAINT chk_incendio_4h
        CHECK (incendio_proximas_4h = 1)
);


CREATE INDEX idx_amostras_positivas_4h_hora
ON tcc.amostras_positivas_4h(hora_referencia);

CREATE INDEX idx_amostras_positivas_4h_segmento_hora
ON tcc.amostras_positivas_4h(segmento_id, hora_referencia);