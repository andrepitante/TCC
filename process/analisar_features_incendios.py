import os
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

print("=" * 90)
print("ANÁLISE ESTATÍSTICA DAS FEATURES DOS INCÊNDIOS")
print("=" * 90)


# ============================================================
# 1. ESTATÍSTICA GERAL
# ============================================================

sql_estatisticas = """
SELECT

    COUNT(*) AS total_registros,

    MIN(temperatura_atual) AS temp_atual_min,
    AVG(temperatura_atual) AS temp_atual_media,
    MAX(temperatura_atual) AS temp_atual_max,

    MIN(temperatura_media_24h) AS temp_media_24h_min,
    AVG(temperatura_media_24h) AS temp_media_24h_media,
    MAX(temperatura_media_24h) AS temp_media_24h_max,

    MIN(temperatura_max_24h) AS temp_max_24h_min,
    AVG(temperatura_max_24h) AS temp_max_24h_media,
    MAX(temperatura_max_24h) AS temp_max_24h_max,

    MIN(umidade_atual) AS umidade_atual_min,
    AVG(umidade_atual) AS umidade_atual_media,
    MAX(umidade_atual) AS umidade_atual_max,

    MIN(umidade_min_24h) AS umidade_min_24h_min,
    AVG(umidade_min_24h) AS umidade_min_24h_media,
    MAX(umidade_min_24h) AS umidade_min_24h_max,

    MIN(vento_atual) AS vento_atual_min,
    AVG(vento_atual) AS vento_atual_media,
    MAX(vento_atual) AS vento_atual_max,

    MIN(rajada_atual) AS rajada_atual_min,
    AVG(rajada_atual) AS rajada_atual_media,
    MAX(rajada_atual) AS rajada_atual_max,

    MIN(chuva_24h) AS chuva_24h_min,
    AVG(chuva_24h) AS chuva_24h_media,
    MAX(chuva_24h) AS chuva_24h_max,

    MIN(chuva_72h) AS chuva_72h_min,
    AVG(chuva_72h) AS chuva_72h_media,
    MAX(chuva_72h) AS chuva_72h_max,

    MIN(chuva_168h) AS chuva_168h_min,
    AVG(chuva_168h) AS chuva_168h_media,
    MAX(chuva_168h) AS chuva_168h_max,

    MIN(horas_com_chuva_24h) AS horas_chuva_24h_min,
    AVG(horas_com_chuva_24h) AS horas_chuva_24h_media,
    MAX(horas_com_chuva_24h) AS horas_chuva_24h_max,

    MIN(horas_com_chuva_72h) AS horas_chuva_72h_min,
    AVG(horas_com_chuva_72h) AS horas_chuva_72h_media,
    MAX(horas_com_chuva_72h) AS horas_chuva_72h_max,

    MIN(horas_sem_chuva_ate_168h) AS horas_secas_min,
    AVG(horas_sem_chuva_ate_168h) AS horas_secas_media,
    MAX(horas_sem_chuva_ate_168h) AS horas_secas_max

FROM tcc.features_incendios;
"""

estatisticas = pd.read_sql(sql_estatisticas, engine)

print("\nESTATÍSTICAS GERAIS")
print("-" * 90)

for coluna in estatisticas.columns:
    print(f"{coluna:35} : {estatisticas.iloc[0][coluna]}")


# ============================================================
# 2. PERCENTIS
# ============================================================

sql_percentis = """
SELECT

    PERCENTILE_CONT(0.01) WITHIN GROUP (ORDER BY temperatura_atual)
        AS temp_p01,

    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY temperatura_atual)
        AS temp_p05,

    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY temperatura_atual)
        AS temp_mediana,

    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY temperatura_atual)
        AS temp_p95,

    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY temperatura_atual)
        AS temp_p99,


    PERCENTILE_CONT(0.01) WITHIN GROUP (ORDER BY umidade_atual)
        AS umidade_p01,

    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY umidade_atual)
        AS umidade_p05,

    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY umidade_atual)
        AS umidade_mediana,

    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY umidade_atual)
        AS umidade_p95,

    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY umidade_atual)
        AS umidade_p99,


    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY chuva_24h)
        AS chuva_24h_mediana,

    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY chuva_24h)
        AS chuva_24h_p90,

    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY chuva_24h)
        AS chuva_24h_p95,

    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY chuva_24h)
        AS chuva_24h_p99,


    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY vento_atual)
        AS vento_mediana,

    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY vento_atual)
        AS vento_p95,

    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY vento_atual)
        AS vento_p99

FROM tcc.features_incendios;
"""

percentis = pd.read_sql(sql_percentis, engine)

print("\nPERCENTIS")
print("-" * 90)

for coluna in percentis.columns:
    print(f"{coluna:35} : {percentis.iloc[0][coluna]}")


# ============================================================
# 3. PROCURA POR VALORES SUSPEITOS
# ============================================================

sql_suspeitos = """
SELECT

    COUNT(*) FILTER (
        WHERE temperatura_atual < -10
           OR temperatura_atual > 50
    ) AS temperatura_atual_suspeita,

    COUNT(*) FILTER (
        WHERE temperatura_max_24h < -10
           OR temperatura_max_24h > 55
    ) AS temperatura_max_suspeita,

    COUNT(*) FILTER (
        WHERE umidade_atual < 0
           OR umidade_atual > 100
    ) AS umidade_atual_suspeita,

    COUNT(*) FILTER (
        WHERE umidade_min_24h < 0
           OR umidade_min_24h > 100
    ) AS umidade_min_suspeita,

    COUNT(*) FILTER (
        WHERE vento_atual < 0
           OR vento_atual > 40
    ) AS vento_atual_suspeito,

    COUNT(*) FILTER (
        WHERE rajada_atual < 0
           OR rajada_atual > 60
    ) AS rajada_atual_suspeita,

    COUNT(*) FILTER (
        WHERE chuva_24h < 0
           OR chuva_24h > 300
    ) AS chuva_24h_suspeita,

    COUNT(*) FILTER (
        WHERE chuva_72h < 0
           OR chuva_72h > 500
    ) AS chuva_72h_suspeita,

    COUNT(*) FILTER (
        WHERE chuva_168h < 0
           OR chuva_168h > 1000
    ) AS chuva_168h_suspeita,

    COUNT(*) FILTER (
        WHERE horas_com_chuva_24h < 0
           OR horas_com_chuva_24h > 24
    ) AS horas_chuva_24h_suspeita,

    COUNT(*) FILTER (
        WHERE horas_com_chuva_72h < 0
           OR horas_com_chuva_72h > 72
    ) AS horas_chuva_72h_suspeita,

    COUNT(*) FILTER (
        WHERE horas_sem_chuva_ate_168h < 0
           OR horas_sem_chuva_ate_168h > 168
    ) AS horas_secas_suspeita

FROM tcc.features_incendios;
"""

suspeitos = pd.read_sql(sql_suspeitos, engine)

print("\nVALORES POTENCIALMENTE SUSPEITOS")
print("-" * 90)

for coluna in suspeitos.columns:
    print(f"{coluna:35} : {suspeitos.iloc[0][coluna]}")


# ============================================================
# 4. VALORES NULOS
# ============================================================

sql_nulos = """
SELECT

    COUNT(*) FILTER (WHERE temperatura_atual IS NULL)
        AS temperatura_atual_null,

    COUNT(*) FILTER (WHERE umidade_atual IS NULL)
        AS umidade_atual_null,

    COUNT(*) FILTER (WHERE precipitacao_atual IS NULL)
        AS precipitacao_atual_null,

    COUNT(*) FILTER (WHERE vento_atual IS NULL)
        AS vento_atual_null,

    COUNT(*) FILTER (WHERE rajada_atual IS NULL)
        AS rajada_atual_null,

    COUNT(*) FILTER (WHERE temperatura_media_24h IS NULL)
        AS temperatura_media_24h_null,

    COUNT(*) FILTER (WHERE temperatura_max_24h IS NULL)
        AS temperatura_max_24h_null,

    COUNT(*) FILTER (WHERE umidade_media_24h IS NULL)
        AS umidade_media_24h_null,

    COUNT(*) FILTER (WHERE umidade_min_24h IS NULL)
        AS umidade_min_24h_null,

    COUNT(*) FILTER (WHERE chuva_24h IS NULL)
        AS chuva_24h_null,

    COUNT(*) FILTER (WHERE chuva_72h IS NULL)
        AS chuva_72h_null,

    COUNT(*) FILTER (WHERE chuva_168h IS NULL)
        AS chuva_168h_null

FROM tcc.features_incendios;
"""

nulos = pd.read_sql(sql_nulos, engine)

print("\nVALORES NULOS")
print("-" * 90)

for coluna in nulos.columns:
    print(f"{coluna:35} : {nulos.iloc[0][coluna]}")


# ============================================================
# 5. DISTRIBUIÇÃO POR RODOVIA
# ============================================================

rodovias = pd.read_sql(
    """
    SELECT
        rodovia,
        COUNT(*) AS quantidade
    FROM tcc.features_incendios
    GROUP BY rodovia
    ORDER BY rodovia;
    """,
    engine
)

print("\nREGISTROS POR RODOVIA")
print("-" * 90)
print(rodovias.to_string(index=False))


# ============================================================
# FIM
# ============================================================

print("\n" + "=" * 90)
print("ANÁLISE CONCLUÍDA")
print("=" * 90)