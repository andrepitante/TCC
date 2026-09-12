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


print("=" * 85)
print("ANÁLISE METEOROLÓGICA HORÁRIA NOS INCÊNDIOS")
print("=" * 85)


# ============================================================
# CONSULTA
#
# Para cada incêndio:
# - arredonda o horário para o início da hora;
# - busca estações até 100 km;
# - escolhe, POR VARIÁVEL, a estação válida mais próxima.
# ============================================================

sql = """
WITH incendios AS
(
    SELECT
        i.id_incendio,
        i.segmento_id,
        i.rodovia,
        i.km,
        i.data_hora_inicio,

        DATE_TRUNC(
            'hour',
            i.data_hora_inicio
        ) AS hora_referencia

    FROM tcc.incendios_segmentados i
),

candidatas AS
(
    SELECT
        i.id_incendio,
        i.segmento_id,
        i.rodovia,
        i.km,
        i.data_hora_inicio,
        i.hora_referencia,

        se.codigo_estacao,
        se.ranking,
        se.distancia_km,

        m.temperatura,
        m.umidade,
        m.precipitacao,
        m.vento_velocidade,
        m.vento_rajada

    FROM incendios i

    JOIN tcc.segmentos_estacoes se
        ON se.segmento_id = i.segmento_id
       AND se.distancia_km <= 100

    LEFT JOIN tcc.meteorologia_raw m
        ON m.codigo_estacao = se.codigo_estacao
       AND m.data_hora = i.hora_referencia
),

resolvido AS
(
    SELECT
        id_incendio,
        segmento_id,
        rodovia,
        km,
        data_hora_inicio,
        hora_referencia,


        -- ====================================================
        -- TEMPERATURA
        -- ====================================================

        (
            ARRAY_AGG(
                temperatura
                ORDER BY distancia_km
            )
            FILTER (
                WHERE temperatura IS NOT NULL
            )
        )[1] AS temperatura,


        (
            ARRAY_AGG(
                codigo_estacao
                ORDER BY distancia_km
            )
            FILTER (
                WHERE temperatura IS NOT NULL
            )
        )[1] AS temperatura_estacao,


        (
            ARRAY_AGG(
                distancia_km
                ORDER BY distancia_km
            )
            FILTER (
                WHERE temperatura IS NOT NULL
            )
        )[1] AS temperatura_distancia_km,


        (
            ARRAY_AGG(
                ranking
                ORDER BY distancia_km
            )
            FILTER (
                WHERE temperatura IS NOT NULL
            )
        )[1] AS temperatura_ranking,


        -- ====================================================
        -- UMIDADE
        -- ====================================================

        (
            ARRAY_AGG(
                umidade
                ORDER BY distancia_km
            )
            FILTER (
                WHERE umidade IS NOT NULL
            )
        )[1] AS umidade,


        (
            ARRAY_AGG(
                codigo_estacao
                ORDER BY distancia_km
            )
            FILTER (
                WHERE umidade IS NOT NULL
            )
        )[1] AS umidade_estacao,


        (
            ARRAY_AGG(
                distancia_km
                ORDER BY distancia_km
            )
            FILTER (
                WHERE umidade IS NOT NULL
            )
        )[1] AS umidade_distancia_km,


        (
            ARRAY_AGG(
                ranking
                ORDER BY distancia_km
            )
            FILTER (
                WHERE umidade IS NOT NULL
            )
        )[1] AS umidade_ranking,


        -- ====================================================
        -- PRECIPITAÇÃO
        -- ====================================================

        (
            ARRAY_AGG(
                precipitacao
                ORDER BY distancia_km
            )
            FILTER (
                WHERE precipitacao IS NOT NULL
            )
        )[1] AS precipitacao,


        (
            ARRAY_AGG(
                codigo_estacao
                ORDER BY distancia_km
            )
            FILTER (
                WHERE precipitacao IS NOT NULL
            )
        )[1] AS precipitacao_estacao,


        (
            ARRAY_AGG(
                distancia_km
                ORDER BY distancia_km
            )
            FILTER (
                WHERE precipitacao IS NOT NULL
            )
        )[1] AS precipitacao_distancia_km,


        (
            ARRAY_AGG(
                ranking
                ORDER BY distancia_km
            )
            FILTER (
                WHERE precipitacao IS NOT NULL
            )
        )[1] AS precipitacao_ranking,


        -- ====================================================
        -- VENTO
        -- ====================================================

        (
            ARRAY_AGG(
                vento_velocidade
                ORDER BY distancia_km
            )
            FILTER (
                WHERE vento_velocidade IS NOT NULL
            )
        )[1] AS vento,


        (
            ARRAY_AGG(
                codigo_estacao
                ORDER BY distancia_km
            )
            FILTER (
                WHERE vento_velocidade IS NOT NULL
            )
        )[1] AS vento_estacao,


        (
            ARRAY_AGG(
                distancia_km
                ORDER BY distancia_km
            )
            FILTER (
                WHERE vento_velocidade IS NOT NULL
            )
        )[1] AS vento_distancia_km,


        (
            ARRAY_AGG(
                ranking
                ORDER BY distancia_km
            )
            FILTER (
                WHERE vento_velocidade IS NOT NULL
            )
        )[1] AS vento_ranking,


        -- ====================================================
        -- RAJADA
        -- ====================================================

        (
            ARRAY_AGG(
                vento_rajada
                ORDER BY distancia_km
            )
            FILTER (
                WHERE vento_rajada IS NOT NULL
            )
        )[1] AS rajada

    FROM candidatas

    GROUP BY
        id_incendio,
        segmento_id,
        rodovia,
        km,
        data_hora_inicio,
        hora_referencia
)

SELECT *
FROM resolvido
ORDER BY data_hora_inicio;
"""


print("\nResolvendo dados meteorológicos dos incêndios...")

df = pd.read_sql(
    sql,
    engine
)

print(f"Incêndios analisados: {len(df):,}")


# ============================================================
# COBERTURA
# ============================================================

variaveis = [
    "temperatura",
    "umidade",
    "precipitacao",
    "vento",
    "rajada",
]


print("\nCobertura após fallback até 100 km:")

for variavel in variaveis:

    validos = df[variavel].notna().sum()

    percentual = (
        validos
        / len(df)
        * 100
    )

    print(
        f"{variavel:15s}: "
        f"{validos:>7,} / {len(df):,} "
        f"({percentual:6.2f}%)"
    )


# ============================================================
# USO DA ESTAÇÃO PRIORITÁRIA X FALLBACK
# ============================================================

print("\nUso do ranking das estações:")

for variavel in [
    "temperatura",
    "umidade",
    "precipitacao",
    "vento",
]:

    coluna = f"{variavel}_ranking"

    dados = df[
        df[coluna].notna()
    ]

    if dados.empty:
        continue

    primeira = (
        dados[coluna] == 1
    ).sum()

    fallback = (
        dados[coluna] > 1
    ).sum()

    total = len(dados)

    print(f"\n{variavel.upper()}")

    print(
        f"Estação ranking 1: "
        f"{primeira:,} "
        f"({primeira / total * 100:.2f}%)"
    )

    print(
        f"Fallback:          "
        f"{fallback:,} "
        f"({fallback / total * 100:.2f}%)"
    )


# ============================================================
# DISTÂNCIAS UTILIZADAS
# ============================================================

print("\nDistâncias das medições utilizadas:")

for variavel in [
    "temperatura",
    "umidade",
    "precipitacao",
    "vento",
]:

    coluna = f"{variavel}_distancia_km"

    serie = df[coluna].dropna()

    if serie.empty:
        continue

    print(
        f"\n{variavel.upper()}"
    )

    print(
        f"Média:    "
        f"{serie.mean():.2f} km"
    )

    print(
        f"Mediana:  "
        f"{serie.median():.2f} km"
    )

    print(
        f"P95:      "
        f"{serie.quantile(0.95):.2f} km"
    )

    print(
        f"Máxima:   "
        f"{serie.max():.2f} km"
    )


# ============================================================
# DISTRIBUIÇÃO DOS RANKINGS
# ============================================================

print("\nDistribuição de ranking utilizado:")

for variavel in [
    "temperatura",
    "umidade",
    "precipitacao",
    "vento",
]:

    coluna = f"{variavel}_ranking"

    print(
        f"\n{variavel.upper()}"
    )

    distribuicao = (
        df[coluna]
        .dropna()
        .astype(int)
        .value_counts()
        .sort_index()
        .head(10)
    )

    print(
        distribuicao.to_string()
    )


# ============================================================
# AMOSTRA
# ============================================================

print("\nAmostra:")

colunas_amostra = [
    "id_incendio",
    "segmento_id",
    "data_hora_inicio",
    "hora_referencia",

    "temperatura",
    "temperatura_estacao",
    "temperatura_distancia_km",

    "umidade",
    "umidade_estacao",

    "precipitacao",
    "precipitacao_estacao",

    "vento",
    "vento_estacao",
]


print(
    df[
        colunas_amostra
    ]
    .head(20)
    .to_string(index=False)
)


print("\n" + "=" * 85)
print("ANÁLISE CONCLUÍDA")
print("=" * 85)