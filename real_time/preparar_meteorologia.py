from pathlib import Path
from datetime import datetime, timedelta
import os
import argparse
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = (
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL)


# =============================================================================
# HORÁRIO DE REFERÊNCIA
# =============================================================================

print("=" * 80)
print("PREPARAÇÃO DA METEOROLOGIA OPERACIONAL")
print("=" * 80)

print()
print("Formato: AAAA-MM-DD HH:MM")
print()

parser = argparse.ArgumentParser(
    description=(
        "Prepara o cache meteorológico "
        "para os 332 segmentos rodoviários."
    )
)

parser.add_argument(
    "hora",
    help=(
        "Hora de referência no formato "
        "'AAAA-MM-DD HH:MM'"
    )
)

args = parser.parse_args()

try:
    hora_referencia = datetime.strptime(
        args.hora,
        "%Y-%m-%d %H:%M"
    )

except ValueError:
    print(
        "ERRO: use o formato "
        "AAAA-MM-DD HH:MM"
    )
    raise SystemExit(1)

if hora_referencia.minute != 0:
    print(
        "ERRO: informe uma hora fechada."
    )
    raise SystemExit(1)


# =============================================================================
# JANELA NECESSÁRIA
# =============================================================================

# Para calcular chuva_168h e horas_sem_chuva_ate_168h
# precisamos das 168 observações horárias terminando na hora de referência.

hora_inicial = hora_referencia - timedelta(hours=167)

print()
print("Hora inicial :", hora_inicial)
print("Hora final   :", hora_referencia)
print("Horas        : 168")


# =============================================================================
# SEGMENTOS
# =============================================================================

segmentos = pd.read_sql(
    """
    SELECT segmento_id
    FROM tcc.segmentos_rodovias
    ORDER BY segmento_id
    """,
    engine
)

qtd_segmentos = len(segmentos)

print()
print("Segmentos    :", qtd_segmentos)


# =============================================================================
# TOTAL TEÓRICO NECESSÁRIO
# =============================================================================

total_necessario = (
    qtd_segmentos * 168
)

print(
    "Registros necessários:",
    f"{total_necessario:,}"
)


# =============================================================================
# VERIFICAR CACHE
# =============================================================================

query_cache = """
SELECT
    COUNT(*) AS quantidade
FROM tcc.meteorologia_segmentos_horaria
WHERE data_hora >= %(hora_inicial)s
  AND data_hora <= %(hora_final)s
"""

cache = pd.read_sql(
    query_cache,
    engine,
    params={
        "hora_inicial": hora_inicial,
        "hora_final": hora_referencia
    }
)

registros_cache = int(
    cache.loc[0, "quantidade"]
)

faltantes = (
    total_necessario
    - registros_cache
)

print()
print("=" * 80)
print("SITUAÇÃO DO CACHE")
print("=" * 80)

print()
print(
    "Necessários :",
    f"{total_necessario:,}"
)

print(
    "No cache    :",
    f"{registros_cache:,}"
)

print(
    "Faltantes   :",
    f"{faltantes:,}"
)

cobertura = (
    registros_cache
    / total_necessario
    * 100
)

print(
    f"Cobertura   : {cobertura:.2f}%"
)


# =============================================================================
# IDENTIFICAR EXATAMENTE OS REGISTROS FALTANTES
# =============================================================================

print()
print("=" * 80)
print("IDENTIFICANDO REGISTROS FALTANTES")
print("=" * 80)

query_faltantes = """
WITH horas AS (
    SELECT generate_series(
        %(hora_inicial)s::timestamp,
        %(hora_final)s::timestamp,
        interval '1 hour'
    ) AS data_hora
),
necessarios AS (
    SELECT
        s.segmento_id,
        h.data_hora
    FROM tcc.segmentos_rodovias s
    CROSS JOIN horas h
)
SELECT
    n.segmento_id,
    n.data_hora
FROM necessarios n
LEFT JOIN tcc.meteorologia_segmentos_horaria m
    ON m.segmento_id = n.segmento_id
   AND m.data_hora = n.data_hora
WHERE m.segmento_id IS NULL
ORDER BY
    n.data_hora,
    n.segmento_id
"""

df_faltantes = pd.read_sql(
    query_faltantes,
    engine,
    params={
        "hora_inicial": hora_inicial,
        "hora_final": hora_referencia
    }
)

print()
print(
    "Faltantes encontrados:",
    f"{len(df_faltantes):,}"
)

print(
    "Segmentos afetados   :",
    df_faltantes["segmento_id"].nunique()
)

if not df_faltantes.empty:

    print()
    print("Primeiros registros:")

    print(
        df_faltantes.head(10).to_string(
            index=False
        )
    )
    
    # =============================================================================
# PREENCHER REGISTROS FALTANTES
# =============================================================================

if not df_faltantes.empty:

    print()
    print("=" * 80)
    print("PREENCHENDO CACHE METEOROLÓGICO")
    print("=" * 80)

    query_preencher = """
    WITH horas AS (
        SELECT generate_series(
            %(hora_inicial)s::timestamp,
            %(hora_final)s::timestamp,
            interval '1 hour'
        ) AS data_hora
    ),

    faltantes AS (
        SELECT
            s.segmento_id,
            h.data_hora
        FROM tcc.segmentos_rodovias s
        CROSS JOIN horas h

        LEFT JOIN tcc.meteorologia_segmentos_horaria cache
            ON cache.segmento_id = s.segmento_id
           AND cache.data_hora = h.data_hora

        WHERE cache.segmento_id IS NULL
    )

    INSERT INTO tcc.meteorologia_segmentos_horaria
    (
        segmento_id,
        data_hora,
        
        temperatura,
        umidade,
        precipitacao,
        vento,
        rajada,

        
        temperatura_estacao,
        temperatura_distancia_km,
        temperatura_ranking,

        umidade_estacao,
        umidade_distancia_km,
        umidade_ranking,

        precipitacao_estacao,
        precipitacao_distancia_km,
        precipitacao_ranking,

        vento_estacao,
        vento_distancia_km,
        vento_ranking,

        rajada_estacao,
        rajada_distancia_km,
        rajada_ranking
        
    )

    SELECT
        f.segmento_id,
        f.data_hora,

        temp.temperatura,
        umi.umidade,
        prec.precipitacao,
        vent.vento,
        raj.rajada,

        temp.codigo_estacao,
        temp.distancia_km,
        temp.ranking,

        umi.codigo_estacao,
        umi.distancia_km,
        umi.ranking,

        prec.codigo_estacao,
        prec.distancia_km,
        prec.ranking,

        vent.codigo_estacao,
        vent.distancia_km,
        vent.ranking,

        raj.codigo_estacao,
        raj.distancia_km,
        raj.ranking

    FROM faltantes f

    LEFT JOIN LATERAL (
        SELECT
            m.temperatura,
            se.codigo_estacao,
            se.distancia_km,
            se.ranking
        FROM tcc.segmentos_estacoes se
        JOIN tcc.meteorologia_raw m
            ON m.codigo_estacao = se.codigo_estacao
           AND m.data_hora = f.data_hora
        WHERE se.segmento_id = f.segmento_id
          AND se.distancia_km <= 100
          AND m.temperatura IS NOT NULL
        ORDER BY se.ranking
        LIMIT 1
    ) temp ON TRUE

    LEFT JOIN LATERAL (
        SELECT
            m.umidade,
            se.codigo_estacao,
            se.distancia_km,
            se.ranking
        FROM tcc.segmentos_estacoes se
        JOIN tcc.meteorologia_raw m
            ON m.codigo_estacao = se.codigo_estacao
           AND m.data_hora = f.data_hora
        WHERE se.segmento_id = f.segmento_id
          AND se.distancia_km <= 100
          AND m.umidade IS NOT NULL
        ORDER BY se.ranking
        LIMIT 1
    ) umi ON TRUE

    LEFT JOIN LATERAL (
        SELECT
            m.precipitacao,
            se.codigo_estacao,
            se.distancia_km,
            se.ranking
        FROM tcc.segmentos_estacoes se
        JOIN tcc.meteorologia_raw m
            ON m.codigo_estacao = se.codigo_estacao
           AND m.data_hora = f.data_hora
        WHERE se.segmento_id = f.segmento_id
          AND se.distancia_km <= 100
          AND m.precipitacao IS NOT NULL
        ORDER BY se.ranking
        LIMIT 1
    ) prec ON TRUE

    LEFT JOIN LATERAL (
        SELECT
            m.vento_velocidade AS vento,
            se.codigo_estacao,
            se.distancia_km,
            se.ranking
        FROM tcc.segmentos_estacoes se
        JOIN tcc.meteorologia_raw m
            ON m.codigo_estacao = se.codigo_estacao
           AND m.data_hora = f.data_hora
        WHERE se.segmento_id = f.segmento_id
          AND se.distancia_km <= 100
          AND m.vento_velocidade IS NOT NULL
        ORDER BY se.ranking
        LIMIT 1
    ) vent ON TRUE

    LEFT JOIN LATERAL (
        SELECT
            m.vento_rajada AS rajada,
            se.codigo_estacao,
            se.distancia_km,
            se.ranking
        FROM tcc.segmentos_estacoes se
        JOIN tcc.meteorologia_raw m
            ON m.codigo_estacao = se.codigo_estacao
           AND m.data_hora = f.data_hora
        WHERE se.segmento_id = f.segmento_id
          AND se.distancia_km <= 100
          AND m.vento_rajada IS NOT NULL
        ORDER BY se.ranking
        LIMIT 1
    ) raj ON TRUE

    ON CONFLICT (segmento_id, data_hora)
    DO NOTHING
    """

    with engine.begin() as conn:

        resultado = conn.exec_driver_sql(
            query_preencher,
            {
                "hora_inicial": hora_inicial,
                "hora_final": hora_referencia
            }
        )

        inseridos = resultado.rowcount

    print()
    print(
        "Registros inseridos:",
        f"{inseridos:,}"
    )

else:

    print()
    print(
        "Cache já está completo."
    )