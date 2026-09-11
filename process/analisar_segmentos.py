import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# ============================================================
# CONEXÃO COM POSTGRESQL
# ============================================================

engine = create_engine(
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# ============================================================
# CONSULTA
# ============================================================

sql = """
SELECT
    id,
    rodovia,
    km,
    municipio,
    latitude,
    longitude,
    data_hora_inicio
FROM tcc.incendios_raw
WHERE
    REPLACE(rodovia, '-', '') IN (
        'SP021',
        'SP280',
        'SP300',
        'SP330',
        'SP348'
    )
    AND km IS NOT NULL;
"""


print("=" * 70)
print("ANÁLISE DOS SEGMENTOS DE 5 KM")
print("=" * 70)

print("\nLendo incêndios do PostgreSQL...")

df = pd.read_sql(sql, engine)

print(f"Registros encontrados: {len(df):,}")


# ============================================================
# NORMALIZAR RODOVIA
# ============================================================

df["rodovia"] = (
    df["rodovia"]
    .str.replace("-", "", regex=False)
    .str.strip()
)

mapa_rodovias = {
    "SP021": "SP-021",
    "SP280": "SP-280",
    "SP300": "SP-300",
    "SP330": "SP-330",
    "SP348": "SP-348",
}

df["rodovia"] = df["rodovia"].map(mapa_rodovias)


# ============================================================
# CRIAR FAIXAS DE 5 KM
# ============================================================

df["km_inicio"] = (df["km"] // 5) * 5
df["km_fim"] = df["km_inicio"] + 5


# ============================================================
# IDENTIFICADOR DO SEGMENTO
# ============================================================

df["segmento_id"] = (
    df["rodovia"]
    + "_"
    + df["km_inicio"].astype(int).astype(str).str.zfill(3)
    + "_"
    + df["km_fim"].astype(int).astype(str).str.zfill(3)
)


# ============================================================
# RESUMO
# ============================================================

resumo = (
    df.groupby(
        [
            "rodovia",
            "segmento_id",
            "km_inicio",
            "km_fim",
        ]
    )
    .size()
    .reset_index(name="incendios")
)


print("\nQuantidade de segmentos com incêndios:")

print(
    resumo.groupby("rodovia")["segmento_id"]
    .nunique()
    .to_string()
)


print("\nQuantidade de incêndios:")

print(
    df.groupby("rodovia")
    .size()
    .to_string()
)


print("\nPrimeiros segmentos:")

print(
    resumo.head(30)
    .to_string(index=False)
)


print("\n" + "=" * 70)
print("ANÁLISE CONCLUÍDA")
print("=" * 70)