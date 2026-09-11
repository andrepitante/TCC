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


# ============================================================
# LER INCÊNDIOS DAS 5 RODOVIAS
# ============================================================

sql = """
SELECT
    id,
    rodovia,
    km,
    municipio,
    latitude,
    longitude,
    data_hora_inicio,
    geom
FROM tcc.incendios_raw
WHERE
    REPLACE(rodovia, '-', '') IN (
        'SP021',
        'SP280',
        'SP300',
        'SP330',
        'SP348'
    )
    AND km IS NOT NULL
    AND data_hora_inicio IS NOT NULL;
"""

print("=" * 75)
print("SEGMENTAÇÃO DOS INCÊNDIOS")
print("=" * 75)

print("\nLendo incêndios...")

df = pd.read_sql(sql, engine)

print(f"Registros lidos: {len(df):,}")


# ============================================================
# NORMALIZAR RODOVIA
# ============================================================

df["rodovia"] = (
    df["rodovia"]
    .str.replace("-", "", regex=False)
    .str.strip()
)

mapa = {
    "SP021": "SP-021",
    "SP280": "SP-280",
    "SP300": "SP-300",
    "SP330": "SP-330",
    "SP348": "SP-348",
}

df["rodovia"] = df["rodovia"].map(mapa)


# ============================================================
# LER SEGMENTOS
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


# ============================================================
# ASSOCIAR INCÊNDIO AO SEGMENTO
# ============================================================

resultado = []

for _, incendio in df.iterrows():

    candidatos = segmentos[
        (segmentos["rodovia"] == incendio["rodovia"])
        & (segmentos["km_inicio"] <= incendio["km"])
        & (segmentos["km_fim"] > incendio["km"])
    ]

    # Caso especial:
    # se o KM for exatamente igual ao km_fim do último segmento
    if candidatos.empty:

        candidatos = segmentos[
            (segmentos["rodovia"] == incendio["rodovia"])
            & (segmentos["km_fim"] == incendio["km"])
        ]

    if candidatos.empty:
        resultado.append({
            "id_incendio": incendio["id"],
            "segmento_id": None,
            "rodovia": incendio["rodovia"],
            "km": incendio["km"],
            "data_hora_inicio": incendio["data_hora_inicio"],
            "data": incendio["data_hora_inicio"].date(),
            "municipio": incendio["municipio"],
            "latitude": incendio["latitude"],
            "longitude": incendio["longitude"],
        })

        continue

    segmento = candidatos.iloc[0]

    resultado.append({
        "id_incendio": incendio["id"],
        "segmento_id": segmento["segmento_id"],
        "rodovia": incendio["rodovia"],
        "km": incendio["km"],
        "data_hora_inicio": incendio["data_hora_inicio"],
        "data": incendio["data_hora_inicio"].date(),
        "municipio": incendio["municipio"],
        "latitude": incendio["latitude"],
        "longitude": incendio["longitude"],
    })


resultado_df = pd.DataFrame(resultado)


# ============================================================
# DIAGNÓSTICO ANTES DE GRAVAR
# ============================================================

total = len(resultado_df)
segmentados = resultado_df["segmento_id"].notna().sum()
nao_segmentados = resultado_df["segmento_id"].isna().sum()

print("\nResultado:")
print(f"Total analisado      : {total:,}")
print(f"Segmentados          : {segmentados:,}")
print(f"Não segmentados      : {nao_segmentados:,}")


if nao_segmentados > 0:

    print("\nRegistros sem segmento:")

    print(
        resultado_df[
            resultado_df["segmento_id"].isna()
        ][
            [
                "id_incendio",
                "rodovia",
                "km",
                "municipio",
                "data_hora_inicio",
            ]
        ]
        .head(50)
        .to_string(index=False)
    )


# ============================================================
# SEGURANÇA
# ============================================================

if nao_segmentados > 0:

    print("\nATENÇÃO:")
    print(
        "Existem incêndios que não encontraram segmento."
    )

    print(
        "Nenhum dado foi gravado no banco."
    )

    raise SystemExit(1)


# ============================================================
# VERIFICAR SE DESTINO ESTÁ VAZIO
# ============================================================

with engine.connect() as conn:

    qtd_destino = conn.execute(
        text("""
        SELECT COUNT(*)
        FROM tcc.incendios_segmentados;
        """)
    ).scalar()

print(f"\nRegistros atualmente no destino: {qtd_destino:,}")

if qtd_destino > 0:

    print("\nA tabela de destino já contém dados.")
    print("Execução interrompida para evitar duplicação.")

    raise SystemExit(1)


# ============================================================
# INSERIR DADOS
# ============================================================

dados_insercao = resultado_df[
    [
        "id_incendio",
        "segmento_id",
        "rodovia",
        "km",
        "data_hora_inicio",
        "data",
        "municipio",
        "latitude",
        "longitude",
    ]
].copy()


dados_insercao.to_sql(
    "incendios_segmentados",
    engine,
    schema="tcc",
    if_exists="append",
    index=False,
)


# ============================================================
# CRIAR GEOMETRIA A PARTIR DE LAT/LON
# ============================================================

with engine.begin() as conn:

    conn.execute(
        text("""
        UPDATE tcc.incendios_segmentados
        SET geom =
            ST_SetSRID(
                ST_MakePoint(longitude, latitude),
                4326
            )
        WHERE
            longitude IS NOT NULL
            AND latitude IS NOT NULL;
        """)
    )


# ============================================================
# RESUMO FINAL
# ============================================================

resumo = pd.read_sql(
    """
    SELECT
        rodovia,
        COUNT(*) AS incendios,
        COUNT(DISTINCT segmento_id) AS segmentos,
        MIN(data) AS primeira_data,
        MAX(data) AS ultima_data
    FROM tcc.incendios_segmentados
    GROUP BY rodovia
    ORDER BY rodovia;
    """,
    engine
)


print("\nResumo final:")

print(
    resumo.to_string(index=False)
)


print("\n" + "=" * 75)
print("PROCESSO CONCLUÍDO")
print("=" * 75)