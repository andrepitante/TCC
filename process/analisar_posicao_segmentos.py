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


# ============================================================
# CONSULTA
#
# Seleciona somente incêndios:
# - já associados a um segmento;
# - com coordenadas;
# - cuja coordenada esteja até 500 m da geometria OSM
#   da própria rodovia.
# ============================================================

sql = """
SELECT
    i.id,
    i.segmento_id,
    i.rodovia,
    i.km,
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


print("=" * 75)
print("ANÁLISE DA POSIÇÃO GEOGRÁFICA DOS SEGMENTOS")
print("=" * 75)

print("\nBuscando coordenadas espacialmente confiáveis...")

df = pd.read_sql(sql, engine)

print(f"Incêndios utilizados: {len(df):,}")


# ============================================================
# POSIÇÃO REPRESENTATIVA
# ============================================================

posicoes = (
    df.groupby(["rodovia", "segmento_id"])
    .agg(
        qtd_pontos=("id", "count"),
        km_min=("km", "min"),
        km_max=("km", "max"),
        latitude_mediana=("latitude", "median"),
        longitude_mediana=("longitude", "median"),
    )
    .reset_index()
)


# ============================================================
# TODOS OS SEGMENTOS
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
    ORDER BY rodovia, numero_segmento;
    """,
    engine
)


resultado = segmentos.merge(
    posicoes,
    on=["rodovia", "segmento_id"],
    how="left"
)


resultado["qtd_pontos"] = (
    resultado["qtd_pontos"]
    .fillna(0)
    .astype(int)
)


# ============================================================
# RESUMO
# ============================================================

print("\nResumo por rodovia:")

resumo = (
    resultado.groupby("rodovia")
    .agg(
        segmentos=("segmento_id", "count"),
        segmentos_com_posicao=(
            "latitude_mediana",
            lambda x: x.notna().sum()
        ),
        segmentos_sem_posicao=(
            "latitude_mediana",
            lambda x: x.isna().sum()
        ),
        pontos_validos=("qtd_pontos", "sum"),
    )
    .reset_index()
)

print(resumo.to_string(index=False))


# ============================================================
# SEGMENTOS COM POUCOS PONTOS
# ============================================================

print("\nSegmentos com menos de 3 pontos confiáveis:")

poucos = resultado[
    resultado["qtd_pontos"] < 3
]

if poucos.empty:

    print("Nenhum.")

else:

    print(
        poucos[
            [
                "segmento_id",
                "rodovia",
                "km_inicio",
                "km_fim",
                "qtd_pontos",
            ]
        ].to_string(index=False)
    )


# ============================================================
# SEGMENTOS SEM POSIÇÃO
# ============================================================

sem_posicao = resultado[
    resultado["latitude_mediana"].isna()
]

print(
    f"\nSegmentos sem nenhuma coordenada confiável: "
    f"{len(sem_posicao)}"
)

if not sem_posicao.empty:

    print(
        sem_posicao[
            [
                "segmento_id",
                "rodovia",
                "km_inicio",
                "km_fim",
            ]
        ].to_string(index=False)
    )


# ============================================================
# AMOSTRA
# ============================================================

print("\nPrimeiros segmentos calculados:")

print(
    resultado[
        [
            "segmento_id",
            "rodovia",
            "km_inicio",
            "km_fim",
            "qtd_pontos",
            "latitude_mediana",
            "longitude_mediana",
        ]
    ]
    .head(20)
    .to_string(index=False)
)


print("\n" + "=" * 75)
print("ANÁLISE CONCLUÍDA")
print("=" * 75)