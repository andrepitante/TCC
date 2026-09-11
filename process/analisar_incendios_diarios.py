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
# CONSULTA - SEGMENTO x DIA
# ============================================================

sql = """
SELECT
    segmento_id,
    rodovia,
    data,
    COUNT(*) AS qtd_incendios
FROM tcc.incendios_segmentados
GROUP BY
    segmento_id,
    rodovia,
    data
ORDER BY
    rodovia,
    segmento_id,
    data;
"""


print("=" * 75)
print("ANÁLISE DE INCÊNDIOS POR SEGMENTO / DIA")
print("=" * 75)

df = pd.read_sql(sql, engine)

print(f"\nCombinações segmento/dia com incêndio: {len(df):,}")
print(f"Total de incêndios: {df['qtd_incendios'].sum():,}")


# ============================================================
# DISTRIBUIÇÃO DA QUANTIDADE DE INCÊNDIOS
# ============================================================

distribuicao = (
    df["qtd_incendios"]
    .value_counts()
    .sort_index()
    .reset_index()
)

distribuicao.columns = [
    "incendios_no_segmento_dia",
    "quantidade_de_dias"
]

print("\nDistribuição:")
print(distribuicao.to_string(index=False))


# ============================================================
# DIAS COM MAIS DE UM INCÊNDIO
# ============================================================

multiplos = df[df["qtd_incendios"] > 1]

print("\nDias/segmentos com mais de um incêndio:")
print(f"{len(multiplos):,}")


if not multiplos.empty:

    print("\nMaiores concentrações:")

    print(
        multiplos
        .sort_values(
            "qtd_incendios",
            ascending=False
        )
        .head(20)
        .to_string(index=False)
    )


# ============================================================
# RESUMO POR RODOVIA
# ============================================================

resumo = (
    df.groupby("rodovia")
    .agg(
        dias_segmento_com_incendio=("data", "size"),
        incendios=("qtd_incendios", "sum"),
        segmentos=("segmento_id", "nunique"),
        primeira_data=("data", "min"),
        ultima_data=("data", "max"),
    )
    .reset_index()
)


print("\nResumo por rodovia:")

print(
    resumo.to_string(index=False)
)


# ============================================================
# DIAS DISTINTOS COM INCÊNDIO
# ============================================================

dias = (
    df.groupby("rodovia")["data"]
    .nunique()
    .reset_index(name="dias_distintos_com_incendio")
)

print("\nDias distintos com algum incêndio na rodovia:")

print(
    dias.to_string(index=False)
)


print("\n" + "=" * 75)
print("ANÁLISE CONCLUÍDA")
print("=" * 75)