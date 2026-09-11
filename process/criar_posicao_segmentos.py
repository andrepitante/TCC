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


print("=" * 75)
print("CRIAÇÃO DAS POSIÇÕES REPRESENTATIVAS DOS SEGMENTOS")
print("=" * 75)


# ============================================================
# VERIFICA SE TABELA DESTINO ESTÁ VAZIA
# ============================================================

with engine.connect() as conn:

    total_destino = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.segmentos_posicao;
        """)
    ).scalar()


print(f"\nRegistros existentes em segmentos_posicao: {total_destino:,}")

if total_destino > 0:
    raise RuntimeError(
        "A tabela tcc.segmentos_posicao já possui registros. "
        "Processo interrompido para evitar duplicação."
    )


# ============================================================
# CONSULTA DOS INCÊNDIOS ESPACIALMENTE CONFIÁVEIS
# ============================================================

sql_incendios = """
SELECT
    i.id,
    i.segmento_id,
    i.rodovia,
    i.latitude,
    i.longitude
FROM tcc.incendios_segmentados i
WHERE
    i.geom IS NOT NULL

    AND EXISTS (
        SELECT 1
        FROM tcc.rodovias_tratadas r
        WHERE
            r.rodovia = i.rodovia

            AND ST_DWithin(
                ST_Transform(i.geom, 31983),
                r.geom_metrica,
                500
            )
    );
"""


print("\nBuscando incêndios espacialmente confiáveis...")

incendios = pd.read_sql(
    sql_incendios,
    engine
)

print(f"Pontos encontrados: {len(incendios):,}")


# ============================================================
# CALCULA MEDIANA POR SEGMENTO
# ============================================================

posicoes = (
    incendios
    .groupby(
        [
            "segmento_id",
            "rodovia"
        ]
    )
    .agg(
        qtd_pontos=("id", "count"),
        latitude=("latitude", "median"),
        longitude=("longitude", "median"),
    )
    .reset_index()
)


posicoes["metodo"] = "mediana_incendios_500m"


print(
    f"Segmentos com posição calculada: "
    f"{len(posicoes):,}"
)


# ============================================================
# BUSCA TODOS OS SEGMENTOS
# ============================================================

segmentos = pd.read_sql(
    """
    SELECT
        segmento_id,
        rodovia,
        numero_segmento,
        km_inicio,
        km_fim
    FROM tcc.segmentos_rodovias
    ORDER BY
        rodovia,
        numero_segmento;
    """,
    engine
)


print(f"Total de segmentos existentes: {len(segmentos):,}")


# ============================================================
# VERIFICA SEGMENTOS SEM POSIÇÃO
# ============================================================

validacao = segmentos.merge(
    posicoes,
    on=[
        "segmento_id",
        "rodovia"
    ],
    how="left"
)


sem_posicao = validacao[
    validacao["latitude"].isna()
]


print(
    f"Segmentos sem posição calculada: "
    f"{len(sem_posicao):,}"
)


if not sem_posicao.empty:

    print("\nSegmentos sem posição:")

    print(
        sem_posicao[
            [
                "segmento_id",
                "rodovia",
                "km_inicio",
                "km_fim"
            ]
        ].to_string(index=False)
    )


# ============================================================
# INSERE SOMENTE SEGMENTOS COM POSIÇÃO
# ============================================================

dados_insert = posicoes[
    [
        "segmento_id",
        "rodovia",
        "qtd_pontos",
        "latitude",
        "longitude",
        "metodo"
    ]
].copy()


print(
    f"\nRegistros que serão inseridos: "
    f"{len(dados_insert):,}"
)


dados_insert.to_sql(
    name="segmentos_posicao",
    schema="tcc",
    con=engine,
    if_exists="append",
    index=False,
    method="multi"
)


# ============================================================
# CRIA GEOMETRIA POINT
# ============================================================

with engine.begin() as conn:

    conn.execute(
        text("""
            UPDATE tcc.segmentos_posicao
            SET geom =
                ST_SetSRID(
                    ST_MakePoint(
                        longitude,
                        latitude
                    ),
                    4326
                )
            WHERE
                longitude IS NOT NULL
                AND latitude IS NOT NULL;
        """)
    )


# ============================================================
# VALIDAÇÃO FINAL
# ============================================================

resumo = pd.read_sql(
    """
    SELECT
        rodovia,
        COUNT(*) AS segmentos_com_posicao,
        SUM(qtd_pontos) AS pontos_utilizados,
        MIN(qtd_pontos) AS menor_qtd_pontos,
        MAX(qtd_pontos) AS maior_qtd_pontos
    FROM tcc.segmentos_posicao
    GROUP BY rodovia
    ORDER BY rodovia;
    """,
    engine
)


print("\nResumo final:")

print(
    resumo.to_string(index=False)
)


with engine.connect() as conn:

    total_final = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.segmentos_posicao;
        """)
    ).scalar()

    total_geom = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.segmentos_posicao
            WHERE geom IS NOT NULL;
        """)
    ).scalar()


print(f"\nTotal inserido: {total_final:,}")
print(f"Com geometria:  {total_geom:,}")


print("\n" + "=" * 75)
print("PROCESSO CONCLUÍDO")
print("=" * 75)