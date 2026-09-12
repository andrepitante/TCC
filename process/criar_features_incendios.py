import os
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)


print("=" * 85)
print("CRIAÇÃO DAS FEATURES METEOROLÓGICAS DOS INCÊNDIOS")
print("=" * 85)


# ============================================================
# VALIDA DESTINO
# ============================================================

with engine.connect() as conn:

    total_destino = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.features_incendios;
        """)
    ).scalar()


print(f"\nRegistros existentes no destino: {total_destino:,}")


if total_destino > 0:

    raise RuntimeError(
        "A tabela tcc.features_incendios já possui registros."
    )


# ============================================================
# CRIA FEATURES
# ============================================================

print("\nCalculando features...")
print("Pode levar alguns minutos.")


sql = """
INSERT INTO tcc.features_incendios
(
    id_incendio,
    segmento_id,
    rodovia,
    data_hora_inicio,
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

    incendio
)

SELECT
    i.id_incendio,
    i.segmento_id,
    i.rodovia,
    i.data_hora_inicio,
    DATE_TRUNC('hour', i.data_hora_inicio) AS hora_referencia,

    atual.temperatura,
    atual.umidade,
    atual.precipitacao,
    atual.vento,
    atual.rajada,

    janela24.temperatura_media,
    janela24.temperatura_max,

    janela24.umidade_media,
    janela24.umidade_min,

    janela24.vento_medio,
    janela24.rajada_max,

    janela24.chuva,
    janela24.horas_com_chuva,

    janela72.chuva,
    janela72.horas_com_chuva,

    janela168.chuva,

    seco.horas_sem_chuva,
    
    janela24.horas_temp,
    janela24.horas_umidade,
    janela24.horas_vento,

    janela24.horas_chuva,
    janela72.horas_chuva,
    janela168.horas_chuva,

    1

FROM tcc.incendios_segmentados i


-- ============================================================
-- CONDIÇÃO DA HORA ATUAL
-- ============================================================

LEFT JOIN LATERAL
(
    SELECT
        m.temperatura,
        m.umidade,
        m.precipitacao,
        m.vento,
        m.rajada

    FROM tcc.meteorologia_segmentos_horaria m

    WHERE
        m.segmento_id = i.segmento_id

        AND m.data_hora =
            DATE_TRUNC(
                'hour',
                i.data_hora_inicio
            )

    LIMIT 1

) atual ON TRUE


-- ============================================================
-- JANELA DE 24 HORAS
--
-- > referência - 24h
-- <= referência
--
-- Isso fornece no máximo 24 observações horárias.
-- ============================================================

LEFT JOIN LATERAL
(
    SELECT
        AVG(m.temperatura) AS temperatura_media,
        MAX(m.temperatura) AS temperatura_max,

        AVG(m.umidade) AS umidade_media,
        MIN(m.umidade) AS umidade_min,

        AVG(m.vento) AS vento_medio,
        MAX(m.rajada) AS rajada_max,

        SUM(m.precipitacao) AS chuva,
        
        COUNT(*) FILTER (
            WHERE m.precipitacao > 0
        ) AS horas_com_chuva,


        COUNT(m.temperatura) AS horas_temp,
        COUNT(m.umidade) AS horas_umidade,
        COUNT(m.vento) AS horas_vento,
        COUNT(m.precipitacao) AS horas_chuva

    FROM tcc.meteorologia_segmentos_horaria m

    WHERE
        m.segmento_id = i.segmento_id

        AND m.data_hora >
            DATE_TRUNC(
                'hour',
                i.data_hora_inicio
            ) - INTERVAL '24 hours'

        AND m.data_hora <=
            DATE_TRUNC(
                'hour',
                i.data_hora_inicio
            )

) janela24 ON TRUE


-- ============================================================
-- JANELA DE 72 HORAS
-- ============================================================

LEFT JOIN LATERAL
(
    SELECT
        SUM(m.precipitacao) AS chuva,
        
        COUNT(*) FILTER (
            WHERE m.precipitacao > 0
        ) AS horas_com_chuva,

        COUNT(m.precipitacao) AS horas_chuva

    FROM tcc.meteorologia_segmentos_horaria m

    WHERE
        m.segmento_id = i.segmento_id

        AND m.data_hora >
            DATE_TRUNC(
                'hour',
                i.data_hora_inicio
            ) - INTERVAL '72 hours'

        AND m.data_hora <=
            DATE_TRUNC(
                'hour',
                i.data_hora_inicio
            )

) janela72 ON TRUE


-- ============================================================
-- JANELA DE 168 HORAS / 7 DIAS
-- ============================================================

LEFT JOIN LATERAL
(
    SELECT
        SUM(m.precipitacao) AS chuva,
        COUNT(m.precipitacao) AS horas_chuva

    FROM tcc.meteorologia_segmentos_horaria m

    WHERE
        m.segmento_id = i.segmento_id

        AND m.data_hora >
            DATE_TRUNC(
                'hour',
                i.data_hora_inicio
            ) - INTERVAL '168 hours'

        AND m.data_hora <=
            DATE_TRUNC(
                'hour',
                i.data_hora_inicio
            )

) janela168 ON TRUE


-- ============================================================
-- HORAS SEM CHUVA
--
-- Procura a última hora com precipitação > 0
-- dentro das últimas 168 horas.
--
-- Se não houver chuva na janela, retorna 168.
-- ============================================================

LEFT JOIN LATERAL
(
    SELECT

        CASE

            -- ------------------------------------------------
            -- Houve chuva dentro da janela:
            -- calcula quantas horas se passaram desde ela.
            -- ------------------------------------------------

            WHEN MAX(m.data_hora) FILTER (
                WHERE m.precipitacao > 0
            ) IS NOT NULL

            THEN

                LEAST(
                    168,

                    FLOOR(
                        EXTRACT(
                            EPOCH FROM
                            (
                                DATE_TRUNC(
                                    'hour',
                                    i.data_hora_inicio
                                )

                                -

                                MAX(m.data_hora) FILTER (
                                    WHERE m.precipitacao > 0
                                )
                            )
                        ) / 3600
                    )::INTEGER
                )


            -- ------------------------------------------------
            -- Não encontramos chuva.
            --
            -- Antes colocávamos 168 automaticamente.
            --
            -- Agora usamos somente a quantidade de horas
            -- realmente observadas.
            -- ------------------------------------------------

            ELSE

                LEAST(
                    168,
                    COUNT(m.precipitacao)::INTEGER
                )

        END AS horas_sem_chuva


    FROM tcc.meteorologia_segmentos_horaria m

    WHERE
        m.segmento_id = i.segmento_id

        AND m.data_hora >
            DATE_TRUNC(
                'hour',
                i.data_hora_inicio
            ) - INTERVAL '168 hours'

        AND m.data_hora <=
            DATE_TRUNC(
                'hour',
                i.data_hora_inicio
            )

) seco ON TRUE
"""


with engine.begin() as conn:
    conn.execute(text(sql))


# ============================================================
# CONTAGEM FINAL
# ============================================================

with engine.connect() as conn:

    total_final = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.features_incendios;
        """)
    ).scalar()


print(f"\nFeatures criadas: {total_final:,}")


# ============================================================
# COBERTURA DAS FEATURES
# ============================================================

cobertura = pd.read_sql(
    """
    SELECT
        COUNT(*) AS total,

        COUNT(temperatura_atual) AS temperatura_atual,
        COUNT(umidade_atual) AS umidade_atual,

        COUNT(temperatura_media_24h) AS temperatura_media_24h,
        COUNT(umidade_min_24h) AS umidade_min_24h,

        COUNT(chuva_24h) AS chuva_24h,
        COUNT(chuva_72h) AS chuva_72h,
        COUNT(chuva_168h) AS chuva_168h,

        COUNT(horas_sem_chuva_ate_168h)
            AS horas_sem_chuva

    FROM tcc.features_incendios;
    """,
    engine
)


print("\nCobertura:")

print(
    cobertura.to_string(index=False)
)


# ============================================================
# QUALIDADE DAS JANELAS
# ============================================================

qualidade = pd.read_sql(
    """
    SELECT

        ROUND(
            AVG(horas_temp_24h)::numeric,
            2
        ) AS media_horas_temp_24h,

        ROUND(
            AVG(horas_umidade_24h)::numeric,
            2
        ) AS media_horas_umidade_24h,

        ROUND(
            AVG(horas_chuva_24h)::numeric,
            2
        ) AS media_horas_chuva_24h,

        ROUND(
            AVG(horas_chuva_72h)::numeric,
            2
        ) AS media_horas_chuva_72h,

        ROUND(
            AVG(horas_chuva_168h)::numeric,
            2
        ) AS media_horas_chuva_168h

    FROM tcc.features_incendios;
    """,
    engine
)


print("\nQuantidade média de horas válidas:")

print(
    qualidade.to_string(index=False)
)


# ============================================================
# AMOSTRA
# ============================================================

amostra = pd.read_sql(
    """
    SELECT
        id_incendio,
        segmento_id,
        data_hora_inicio,

        temperatura_atual,
        umidade_atual,
        vento_atual,

        temperatura_media_24h,
        temperatura_max_24h,

        umidade_media_24h,
        umidade_min_24h,

        chuva_24h,
        horas_com_chuva_24h,

        chuva_72h,
        horas_com_chuva_72h,

        chuva_168h,
        horas_sem_chuva_ate_168h
        
    FROM tcc.features_incendios

    ORDER BY data_hora_inicio

    LIMIT 20;
    """,
    engine
)


print("\nAmostra:")

print(
    amostra.to_string(index=False)
)


print("\n" + "=" * 85)
print("PROCESSO CONCLUÍDO")
print("=" * 85)