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


print("=" * 80)
print("CRIAÇÃO DO RANKING DE ESTAÇÕES POR SEGMENTO")
print("=" * 80)


# ============================================================
# VALIDAÇÕES
# ============================================================

with engine.connect() as conn:

    total_segmentos = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.segmentos_posicao;
        """)
    ).scalar()

    total_estacoes = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.estacoes_meteorologicas;
        """)
    ).scalar()

    total_destino = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.segmentos_estacoes;
        """)
    ).scalar()


print(f"\nSegmentos com posição: {total_segmentos:,}")
print(f"Estações meteorológicas: {total_estacoes:,}")
print(f"Registros existentes no destino: {total_destino:,}")


if total_segmentos == 0:
    raise RuntimeError(
        "Nenhum segmento com posição encontrado."
    )


if total_estacoes == 0:
    raise RuntimeError(
        "Nenhuma estação meteorológica encontrada."
    )


if total_destino > 0:
    raise RuntimeError(
        "tcc.segmentos_estacoes já possui registros. "
        "Processo interrompido para evitar duplicação."
    )


esperado = total_segmentos * total_estacoes

print(f"Combinações esperadas: {esperado:,}")


# ============================================================
# CALCULA DISTÂNCIAS E RANKING
# ============================================================

print("\nCalculando distâncias...")


sql_insert = """
INSERT INTO tcc.segmentos_estacoes
(
    segmento_id,
    codigo_estacao,
    distancia_km,
    ranking
)

SELECT
    segmento_id,
    codigo_estacao,
    distancia_km,

    ROW_NUMBER() OVER (
        PARTITION BY segmento_id
        ORDER BY
            distancia_km,
            codigo_estacao
    ) AS ranking

FROM
(
    SELECT
        sp.segmento_id,

        e.codigo_estacao,

        ST_Distance(
            sp.geom::geography,
            e.geom::geography
        ) / 1000.0 AS distancia_km

    FROM tcc.segmentos_posicao sp

    CROSS JOIN tcc.estacoes_meteorologicas e

    WHERE
        sp.geom IS NOT NULL
        AND e.geom IS NOT NULL

) distancias;
"""


with engine.begin() as conn:
    conn.execute(text(sql_insert))


# ============================================================
# VALIDAÇÃO FINAL
# ============================================================

with engine.connect() as conn:

    total_final = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.segmentos_estacoes;
        """)
    ).scalar()


print(f"\nRegistros inseridos: {total_final:,}")


if total_final != esperado:

    raise RuntimeError(
        f"Quantidade inesperada. "
        f"Esperado: {esperado:,} | "
        f"Inserido: {total_final:,}"
    )


# ============================================================
# RESUMO DAS CINCO ESTAÇÕES MAIS PRÓXIMAS
# ============================================================

resumo = pd.read_sql(
    """
    SELECT
        se.segmento_id,
        sr.rodovia,
        sr.km_inicio,
        sr.km_fim,
        se.ranking,
        se.codigo_estacao,
        e.nome AS nome_estacao,
        ROUND(
            se.distancia_km::numeric,
            2
        ) AS distancia_km

    FROM tcc.segmentos_estacoes se

    JOIN tcc.segmentos_rodovias sr
        ON sr.segmento_id = se.segmento_id

    JOIN tcc.estacoes_meteorologicas e
        ON e.codigo_estacao = se.codigo_estacao

    WHERE se.ranking <= 5

    ORDER BY
        sr.rodovia,
        sr.numero_segmento,
        se.ranking;
    """,
    engine
)


print("\nExemplo das estações mais próximas:")

print(
    resumo.head(25).to_string(
        index=False
    )
)


# ============================================================
# ESTATÍSTICAS POR RANKING
# ============================================================

estatisticas = pd.read_sql(
    """
    SELECT
        ranking,

        ROUND(
            MIN(distancia_km)::numeric,
            2
        ) AS menor_km,

        ROUND(
            AVG(distancia_km)::numeric,
            2
        ) AS media_km,

        ROUND(
            PERCENTILE_CONT(0.5)
            WITHIN GROUP (
                ORDER BY distancia_km
            )::numeric,
            2
        ) AS mediana_km,

        ROUND(
            MAX(distancia_km)::numeric,
            2
        ) AS maior_km

    FROM tcc.segmentos_estacoes

    WHERE ranking <= 10

    GROUP BY ranking

    ORDER BY ranking;
    """,
    engine
)


print("\nDistância das estações por ranking:")

print(
    estatisticas.to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("PROCESSO CONCLUÍDO")
print("=" * 80)