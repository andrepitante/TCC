import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, URL


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME"),
)

engine = create_engine(url)


print("=" * 90)
print("GERAÇÃO DAS FEATURES DAS AMOSTRAS NEGATIVAS - HORIZONTE 4H")
print("=" * 90)


# =============================================================================
# CONTAGEM INICIAL
# =============================================================================

with engine.connect() as conn:

    total_negativas = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.amostras_negativas_4h;
        """)
    ).scalar_one()

    total_features = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.features_negativas_4h;
        """)
    ).scalar_one()

    anos = conn.execute(
        text("""
            SELECT DISTINCT EXTRACT(YEAR FROM hora_referencia)::int AS ano
            FROM tcc.amostras_negativas_4h
            ORDER BY ano;
        """)
    ).scalars().all()


print()
print(f"Amostras negativas : {total_negativas:,}")
print(f"Features existentes: {total_features:,}")
print(f"Anos encontrados   : {anos}")


# =============================================================================
# SQL DAS FEATURES
# =============================================================================

sql_features = text("""
INSERT INTO tcc.features_negativas_4h (

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
)

SELECT

    n.segmento_id,
    n.rodovia,
    n.hora_referencia,

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

        -- Nenhuma informação de chuva disponível
        WHEN hist.horas_chuva_168h = 0
            THEN NULL

        -- Existe informação meteorológica,
        -- mas não houve chuva no período disponível
        WHEN hist.ultima_hora_com_chuva IS NULL
            THEN hist.horas_chuva_168h

        -- Horas desde a última ocorrência de chuva
        ELSE LEAST(
            168,
            FLOOR(
                EXTRACT(
                    EPOCH FROM (
                        n.hora_referencia
                        - hist.ultima_hora_com_chuva
                    )
                ) / 3600
            )::integer
        )

    END AS horas_sem_chuva_ate_168h,

    hist.horas_temp_24h,
    hist.horas_umidade_24h,
    hist.horas_vento_24h,

    hist.horas_chuva_24h,
    hist.horas_chuva_72h,
    hist.horas_chuva_168h,

    0 AS incendio_proximas_4h


FROM tcc.amostras_negativas_4h n


-- ============================================================================
-- VALORES DA HORA DE REFERÊNCIA
-- ============================================================================

LEFT JOIN tcc.meteorologia_segmentos_horaria atual

    ON atual.segmento_id = n.segmento_id
   AND atual.data_hora = n.hora_referencia


-- ============================================================================
-- HISTÓRICO DAS ÚLTIMAS 168 HORAS
-- ============================================================================

LEFT JOIN LATERAL (

    SELECT

        -- --------------------------------------------------------------------
        -- TEMPERATURA - 24H
        -- --------------------------------------------------------------------

        AVG(m.temperatura)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS temperatura_media_24h,

        MAX(m.temperatura)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS temperatura_max_24h,


        -- --------------------------------------------------------------------
        -- UMIDADE - 24H
        -- --------------------------------------------------------------------

        AVG(m.umidade)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS umidade_media_24h,

        MIN(m.umidade)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS umidade_min_24h,


        -- --------------------------------------------------------------------
        -- VENTO / RAJADA - 24H
        -- --------------------------------------------------------------------

        AVG(m.vento)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS vento_medio_24h,

        MAX(m.rajada)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS rajada_max_24h,


        -- --------------------------------------------------------------------
        -- CHUVA - 24H
        -- --------------------------------------------------------------------

        SUM(m.precipitacao)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS chuva_24h,

        COUNT(*)
            FILTER (
                WHERE
                    m.data_hora > n.hora_referencia - INTERVAL '24 hours'
                    AND m.precipitacao > 0
            ) AS horas_com_chuva_24h,


        -- --------------------------------------------------------------------
        -- CHUVA - 72H
        -- --------------------------------------------------------------------

        SUM(m.precipitacao)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '72 hours'
            ) AS chuva_72h,

        COUNT(*)
            FILTER (
                WHERE
                    m.data_hora > n.hora_referencia - INTERVAL '72 hours'
                    AND m.precipitacao > 0
            ) AS horas_com_chuva_72h,


        -- --------------------------------------------------------------------
        -- CHUVA - 168H
        -- --------------------------------------------------------------------

        SUM(m.precipitacao) AS chuva_168h,


        -- --------------------------------------------------------------------
        -- ÚLTIMA HORA COM CHUVA
        -- --------------------------------------------------------------------

        MAX(m.data_hora)
            FILTER (
                WHERE m.precipitacao > 0
            ) AS ultima_hora_com_chuva,


        -- --------------------------------------------------------------------
        -- CONTROLE DE COBERTURA
        -- --------------------------------------------------------------------

        COUNT(m.temperatura)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS horas_temp_24h,

        COUNT(m.umidade)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS horas_umidade_24h,

        COUNT(m.vento)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS horas_vento_24h,

        COUNT(m.precipitacao)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '24 hours'
            ) AS horas_chuva_24h,

        COUNT(m.precipitacao)
            FILTER (
                WHERE m.data_hora > n.hora_referencia - INTERVAL '72 hours'
            ) AS horas_chuva_72h,

        COUNT(m.precipitacao) AS horas_chuva_168h


    FROM tcc.meteorologia_segmentos_horaria m

    WHERE
        m.segmento_id = n.segmento_id

        AND m.data_hora
            > n.hora_referencia - INTERVAL '168 hours'

        AND m.data_hora
            <= n.hora_referencia

) hist ON TRUE


WHERE
    EXTRACT(YEAR FROM n.hora_referencia)::int = :ano


ON CONFLICT (segmento_id, hora_referencia)

DO UPDATE SET

    rodovia = EXCLUDED.rodovia,

    temperatura_atual = EXCLUDED.temperatura_atual,
    umidade_atual = EXCLUDED.umidade_atual,
    precipitacao_atual = EXCLUDED.precipitacao_atual,
    vento_atual = EXCLUDED.vento_atual,
    rajada_atual = EXCLUDED.rajada_atual,

    temperatura_media_24h = EXCLUDED.temperatura_media_24h,
    temperatura_max_24h = EXCLUDED.temperatura_max_24h,

    umidade_media_24h = EXCLUDED.umidade_media_24h,
    umidade_min_24h = EXCLUDED.umidade_min_24h,

    vento_medio_24h = EXCLUDED.vento_medio_24h,
    rajada_max_24h = EXCLUDED.rajada_max_24h,

    chuva_24h = EXCLUDED.chuva_24h,
    horas_com_chuva_24h = EXCLUDED.horas_com_chuva_24h,

    chuva_72h = EXCLUDED.chuva_72h,
    horas_com_chuva_72h = EXCLUDED.horas_com_chuva_72h,

    chuva_168h = EXCLUDED.chuva_168h,
    horas_sem_chuva_ate_168h = EXCLUDED.horas_sem_chuva_ate_168h,

    horas_temp_24h = EXCLUDED.horas_temp_24h,
    horas_umidade_24h = EXCLUDED.horas_umidade_24h,
    horas_vento_24h = EXCLUDED.horas_vento_24h,

    horas_chuva_24h = EXCLUDED.horas_chuva_24h,
    horas_chuva_72h = EXCLUDED.horas_chuva_72h,
    horas_chuva_168h = EXCLUDED.horas_chuva_168h,

    incendio_proximas_4h = 0;
""")


# =============================================================================
# PROCESSAMENTO ANO A ANO
# =============================================================================

for ano in anos:

    print()
    print("=" * 90)
    print(f"PROCESSANDO {ano}")
    print("=" * 90)

    with engine.connect() as conn:

        qtd_ano = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM tcc.amostras_negativas_4h
                WHERE EXTRACT(YEAR FROM hora_referencia)::int = :ano;
            """),
            {"ano": ano},
        ).scalar_one()

    print(f"Amostras negativas no ano: {qtd_ano:,}")
    print("Calculando features...")

    with engine.begin() as conn:
        conn.execute(
            sql_features,
            {"ano": ano},
        )

    with engine.connect() as conn:

        features_ano = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM tcc.features_negativas_4h
                WHERE EXTRACT(YEAR FROM hora_referencia)::int = :ano;
            """),
            {"ano": ano},
        ).scalar_one()

    print(f"Features gravadas no ano  : {features_ano:,}")

    if features_ano == qtd_ano:
        print("Validação                 : OK")
    else:
        print("Validação                 : ATENÇÃO")


# =============================================================================
# RESULTADO FINAL
# =============================================================================

with engine.connect() as conn:

    total_final = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.features_negativas_4h;
        """)
    ).scalar_one()

    duplicados = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM (
                SELECT
                    segmento_id,
                    hora_referencia
                FROM tcc.features_negativas_4h
                GROUP BY
                    segmento_id,
                    hora_referencia
                HAVING COUNT(*) > 1
            ) x;
        """)
    ).scalar_one()


print()
print("=" * 90)
print("RESULTADO FINAL")
print("=" * 90)

print()
print(f"Amostras negativas esperadas : {total_negativas:,}")
print(f"Features negativas criadas   : {total_final:,}")
print(f"Duplicidades                  : {duplicados:,}")

if total_final == total_negativas and duplicados == 0:

    print()
    print("VALIDAÇÃO FINAL: OK")

else:

    print()
    print("VALIDAÇÃO FINAL: ATENÇÃO")


print()
print("=" * 90)
print("PROCESSO CONCLUÍDO")
print("=" * 90)