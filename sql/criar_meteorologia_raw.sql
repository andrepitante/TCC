DROP TABLE IF EXISTS tcc.meteorologia_raw;

CREATE TABLE tcc.meteorologia_raw (

    id BIGSERIAL PRIMARY KEY,

    codigo_estacao VARCHAR(10) NOT NULL,

    data DATE NOT NULL,

    hora TIME WITHOUT TIME ZONE NOT NULL,

    data_hora TIMESTAMP WITHOUT TIME ZONE NOT NULL,


    -- ========================================================
    -- PRECIPITAÇÃO
    -- ========================================================

    precipitacao DOUBLE PRECISION,


    -- ========================================================
    -- PRESSÃO
    -- ========================================================

    pressao_estacao DOUBLE PRECISION,

    pressao_nivel_mar DOUBLE PRECISION,

    pressao_max DOUBLE PRECISION,

    pressao_min DOUBLE PRECISION,


    -- ========================================================
    -- RADIAÇÃO
    -- ========================================================

    radiacao_global DOUBLE PRECISION,


    -- ========================================================
    -- TEMPERATURA
    -- ========================================================

    temperatura DOUBLE PRECISION,

    temperatura_orvalho DOUBLE PRECISION,

    temperatura_max DOUBLE PRECISION,

    temperatura_min DOUBLE PRECISION,

    temperatura_orvalho_max DOUBLE PRECISION,

    temperatura_orvalho_min DOUBLE PRECISION,


    -- ========================================================
    -- UMIDADE
    -- ========================================================

    umidade_max DOUBLE PRECISION,

    umidade_min DOUBLE PRECISION,

    umidade DOUBLE PRECISION,


    -- ========================================================
    -- VENTO
    -- ========================================================

    vento_direcao DOUBLE PRECISION,

    vento_rajada DOUBLE PRECISION,

    vento_velocidade DOUBLE PRECISION,


    -- ========================================================
    -- AUDITORIA
    -- ========================================================

    arquivo_origem TEXT,

    criado_em TIMESTAMP WITHOUT TIME ZONE
        DEFAULT CURRENT_TIMESTAMP,


    CONSTRAINT fk_meteorologia_estacao
        FOREIGN KEY (codigo_estacao)
        REFERENCES tcc.estacoes_meteorologicas(codigo_estacao),

    CONSTRAINT uq_meteorologia_estacao_datahora
        UNIQUE (codigo_estacao, data_hora)
);


-- ============================================================
-- ÍNDICES
-- ============================================================

CREATE INDEX idx_meteorologia_raw_estacao
ON tcc.meteorologia_raw (codigo_estacao);


CREATE INDEX idx_meteorologia_raw_data
ON tcc.meteorologia_raw (data);


CREATE INDEX idx_meteorologia_raw_data_hora
ON tcc.meteorologia_raw (data_hora);


CREATE INDEX idx_meteorologia_raw_estacao_data
ON tcc.meteorologia_raw (
    codigo_estacao,
    data
);