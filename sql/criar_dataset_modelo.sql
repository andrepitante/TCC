DROP TABLE IF EXISTS tcc.dataset_modelo;

CREATE TABLE tcc.dataset_modelo AS

-- ============================================================
-- POSITIVAS
-- ============================================================

SELECT
    segmento_id,
    rodovia,
    hora_referencia,

    temperatura_atual,
    umidade_atual,
    precipitacao_atual,
    vento_atual,
    rajada_atual,

    temperatura_media_24h,
    temperatura_max_24h,
    umidade_media_24h,
    umidade_min_24h,
    vento_medio_24h,
    rajada_max_24h,

    chuva_24h,
    horas_com_chuva_24h,
    chuva_72h,
    horas_com_chuva_72h,
    chuva_168h,
    horas_sem_chuva_ate_168h,

    horas_temp_24h,
    horas_umidade_24h,
    horas_vento_24h,
    horas_chuva_24h,
    horas_chuva_72h,
    horas_chuva_168h,

    incendio_proximas_4h

FROM tcc.features_positivas_4h


UNION ALL


-- ============================================================
-- NEGATIVAS
-- ============================================================

SELECT
    segmento_id,
    rodovia,
    hora_referencia,

    temperatura_atual,
    umidade_atual,
    precipitacao_atual,
    vento_atual,
    rajada_atual,

    temperatura_media_24h,
    temperatura_max_24h,
    umidade_media_24h,
    umidade_min_24h,
    vento_medio_24h,
    rajada_max_24h,

    chuva_24h,
    horas_com_chuva_24h,
    chuva_72h,
    horas_com_chuva_72h,
    chuva_168h,
    horas_sem_chuva_ate_168h,

    horas_temp_24h,
    horas_umidade_24h,
    horas_vento_24h,
    horas_chuva_24h,
    horas_chuva_72h,
    horas_chuva_168h,

    incendio_proximas_4h

FROM tcc.features_negativas_4h;


-- ============================================================
-- ÍNDICES
-- ============================================================

CREATE INDEX idx_dataset_modelo_hora
    ON tcc.dataset_modelo (hora_referencia);

CREATE INDEX idx_dataset_modelo_segmento_hora
    ON tcc.dataset_modelo (segmento_id, hora_referencia);

CREATE INDEX idx_dataset_modelo_classe
    ON tcc.dataset_modelo (incendio_proximas_4h);