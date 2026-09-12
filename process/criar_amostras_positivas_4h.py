import os

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


print("=" * 90)
print("CRIAÇÃO DAS FEATURES POSITIVAS - HORIZONTE DE 4 HORAS")
print("=" * 90)


# ============================================================
# VALIDAÇÕES
# ============================================================

with engine.connect() as conn:

    total_amostras = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.amostras_positivas_4h;
        """)
    ).scalar()

    total_destino = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.features_positivas_4h;
        """)
    ).scalar()


print(f"\nAmostras positivas disponíveis : {total_amostras:,}")
print(f"Features já existentes         : {total_destino:,}")


if total_destino > 0:
    raise RuntimeError(
        "A tabela tcc.features_positivas_4h já possui registros."
    )


# ============================================================
# CRIA FEATURES
# ============================================================

print("\nCalculando features meteorológicas...")
print("Essa etapa pode levar alguns minutos.")


sql = """
INSERT INTO tcc.features_positivas_4h
(
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

    primeira_ocorrencia,
    minutos_ate_incendio,
    qtd_incendios_janela,

    incendio_proximas_4h
)

SELECT

    a.segmento_id,
    a.rodovia,
    a.hora_referencia,

    atual.temperatura,
    atual.umidade,
    atual.precipitacao,
    atual.vento,
    atual.rajada,

    hist.temperatura_media_24h,
    hist.temperatura_max_24h,

    hist.umidade_media_24h,
    hist.umidade_min_24h,

    hist.vento_medio_24h,
    hist.rajada_max_24h,

    hist.chuva_24h,
    hist.horas_com_chuva_24h,

    hist.chuva_72h,
    hist.horas_com_chuva_72h,

    hist.chuva_168h,

    CASE
        WHEN hist.ultima_chuva_168h IS NOT NULL
        THEN FLOOR(
            EXTRACT(
                EPOCH FROM (
                    a.hora_referencia - hist.ultima_chuva_168h
                )
            ) / 3600
        )::INTEGER

        ELSE LEAST(
            168,
            hist.horas_chuva_168h
        )
    END AS horas_sem_chuva_ate_168h,

    hist.horas_temp_24h,
    hist.horas_umidade_24h,
    hist.horas_vento_24h,

    hist.horas_chuva_24h,
    hist.horas_chuva_72h,
    hist.horas_chuva_168h,

    a.primeira_ocorrencia,
    a.minutos_ate_incendio,
    a.qtd_incendios_janela,

    1

FROM tcc.amostras_positivas_4h a


-- ============================================================
-- CLIMA DA HORA DE REFERÊNCIA
-- ============================================================

LEFT JOIN tcc.meteorologia_segmentos_horaria atual
    ON atual.segmento_id = a.segmento_id
   AND atual.data_hora = a.hora_referencia


-- ============================================================
-- HISTÓRICO ATÉ 168 HORAS
-- ============================================================

LEFT JOIN LATERAL
(
    SELECT

        -- temperatura 24h
        AVG(m.temperatura) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        ) AS temperatura_media_24h,

        MAX(m.temperatura) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        ) AS temperatura_max_24h,


        -- umidade 24h
        AVG(m.umidade) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        ) AS umidade_media_24h,

        MIN(m.umidade) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        ) AS umidade_min_24h,


        -- vento 24h
        AVG(m.vento) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        ) AS vento_medio_24h,

        MAX(m.rajada) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        ) AS rajada_max_24h,


        -- chuva 24h
        SUM(m.precipitacao) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        ) AS chuva_24h,

        COUNT(*) FILTER (
            WHERE
                m.data_hora >
                    a.hora_referencia - INTERVAL '24 hours'
                AND m.precipitacao > 0
        )::INTEGER AS horas_com_chuva_24h,


        -- chuva 72h
        SUM(m.precipitacao) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '72 hours'
        ) AS chuva_72h,

        COUNT(*) FILTER (
            WHERE
                m.data_hora >
                    a.hora_referencia - INTERVAL '72 hours'
                AND m.precipitacao > 0
        )::INTEGER AS horas_com_chuva_72h,


        -- chuva 168h
        SUM(m.precipitacao) AS chuva_168h,

        MAX(m.data_hora) FILTER (
            WHERE m.precipitacao > 0
        ) AS ultima_chuva_168h,


        -- cobertura 24h
        COUNT(m.temperatura) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        )::INTEGER AS horas_temp_24h,

        COUNT(m.umidade) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        )::INTEGER AS horas_umidade_24h,

        COUNT(m.vento) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        )::INTEGER AS horas_vento_24h,

        COUNT(m.precipitacao) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '24 hours'
        )::INTEGER AS horas_chuva_24h,


        -- cobertura 72h
        COUNT(m.precipitacao) FILTER (
            WHERE m.data_hora >
                a.hora_referencia - INTERVAL '72 hours'
        )::INTEGER AS horas_chuva_72h,


        -- cobertura 168h
        COUNT(m.precipitacao)::INTEGER
            AS horas_chuva_168h


    FROM tcc.meteorologia_segmentos_horaria m

    WHERE
        m.segmento_id = a.segmento_id

        AND m.data_hora >
            a.hora_referencia - INTERVAL '168 hours'

        AND m.data_hora <=
            a.hora_referencia

) hist ON TRUE;
"""


with engine.begin() as conn:
    conn.execute(text(sql))


# ============================================================
# VALIDA RESULTADO
# ============================================================

with engine.connect() as conn:

    total_final = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.features_positivas_4h;
        """)
    ).scalar()

    resumo = conn.execute(
        text("""
            SELECT

                COUNT(*) AS total,

                COUNT(temperatura_atual)
                    AS temperatura_atual,

                COUNT(umidade_atual)
                    AS umidade_atual,

                COUNT(chuva_24h)
                    AS chuva_24h,

                COUNT(chuva_72h)
                    AS chuva_72h,

                COUNT(chuva_168h)
                    AS chuva_168h,

                ROUND(
                    AVG(horas_chuva_168h)::numeric,
                    2
                ) AS media_horas_chuva_168h

            FROM tcc.features_positivas_4h;
        """)
    ).mappings().one()


print("\n" + "=" * 90)
print("RESULTADO")
print("=" * 90)

print(f"\nFeatures criadas: {total_final:,}")

print(
    f"Temperatura atual : "
    f"{resumo['temperatura_atual']:,}"
)

print(
    f"Umidade atual     : "
    f"{resumo['umidade_atual']:,}"
)

print(
    f"Chuva 24h         : "
    f"{resumo['chuva_24h']:,}"
)

print(
    f"Chuva 72h         : "
    f"{resumo['chuva_72h']:,}"
)

print(
    f"Chuva 168h        : "
    f"{resumo['chuva_168h']:,}"
)

print(
    f"Média cobertura 168h: "
    f"{resumo['media_horas_chuva_168h']}"
)


print("\n" + "=" * 90)
print("PROCESSO CONCLUÍDO")
print("=" * 90)