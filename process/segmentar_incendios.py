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
# FAIXAS ANALÍTICAS DAS RODOVIAS
# ============================================================

faixas_rodovias = {
    "SP-021": (0, 135),
    "SP-280": (10, 320),
    "SP-300": (60, 670),
    "SP-330": (10, 450),
    "SP-348": (10, 175),
}


print("=" * 75)
print("SEGMENTAÇÃO DOS INCÊNDIOS POR TRECHOS DE 5 KM")
print("=" * 75)


# ============================================================
# VERIFICA TABELA DESTINO
# ============================================================

with engine.connect() as conn:
    total_destino = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.incendios_segmentados;
        """)
    ).scalar()

print(f"\nRegistros existentes em incendios_segmentados: {total_destino:,}")

if total_destino > 0:
    raise RuntimeError(
        "A tabela tcc.incendios_segmentados já possui registros. "
        "Processo interrompido para evitar duplicação."
    )


# ============================================================
# CARREGA SEGMENTOS
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

print(f"Segmentos carregados: {len(segmentos):,}")


# ============================================================
# CARREGA INCÊNDIOS
# ============================================================

sql_incendios = """
SELECT
    id,
    rodovia,
    km,
    data_hora_inicio,
    municipio,
    latitude,
    longitude
FROM tcc.incendios_raw
WHERE
    rodovia IS NOT NULL
    AND km IS NOT NULL
    AND data_hora_inicio IS NOT NULL;
"""

incendios = pd.read_sql(sql_incendios, engine)


# ============================================================
# NORMALIZA NOME DA RODOVIA
# ============================================================

def normalizar_rodovia(valor):
    if valor is None:
        return None

    valor = str(valor).upper().strip()

    somente_numeros = "".join(
        caractere
        for caractere in valor
        if caractere.isdigit()
    )

    if not somente_numeros:
        return None

    try:
        numero = int(somente_numeros)
    except ValueError:
        return None

    return f"SP-{numero:03d}"


incendios["rodovia_normalizada"] = incendios["rodovia"].apply(
    normalizar_rodovia
)


# ============================================================
# MANTÉM SOMENTE AS CINCO RODOVIAS DO ESTUDO
# ============================================================

incendios = incendios[
    incendios["rodovia_normalizada"].isin(
        faixas_rodovias.keys()
    )
].copy()

print(f"Incêndios analisados: {len(incendios):,}")


# ============================================================
# SEGMENTAÇÃO
# ============================================================

registros_segmentados = []
fora_area_estudo = []
erros_segmentacao = []


for _, incendio in incendios.iterrows():

    rodovia = incendio["rodovia_normalizada"]
    km = float(incendio["km"])

    km_min, km_max = faixas_rodovias[rodovia]

    # --------------------------------------------------------
    # FORA DA ÁREA ANALÍTICA
    # --------------------------------------------------------

    if km < km_min or km >= km_max:

        fora_area_estudo.append(
            {
                "id": incendio["id"],
                "rodovia": rodovia,
                "km": km,
                "data_hora_inicio": incendio["data_hora_inicio"],
                "municipio": incendio["municipio"],
            }
        )

        continue


    # --------------------------------------------------------
    # PROCURA SEGMENTO
    # --------------------------------------------------------

    candidatos = segmentos[
        (segmentos["rodovia"] == rodovia)
        & (segmentos["km_inicio"] <= km)
        & (segmentos["km_fim"] > km)
    ]


    # --------------------------------------------------------
    # TRATAMENTO PARA KM EXATAMENTE IGUAL AO LIMITE FINAL
    # --------------------------------------------------------

    if candidatos.empty:

        candidatos = segmentos[
            (segmentos["rodovia"] == rodovia)
            & (segmentos["km_fim"] == km)
            & (segmentos["km_fim"] == km_max)
        ]


    # --------------------------------------------------------
    # ERRO REAL DE SEGMENTAÇÃO
    # --------------------------------------------------------

    if candidatos.empty:

        erros_segmentacao.append(
            {
                "id": incendio["id"],
                "rodovia": rodovia,
                "km": km,
                "data_hora_inicio": incendio["data_hora_inicio"],
                "municipio": incendio["municipio"],
            }
        )

        continue


    segmento = candidatos.iloc[0]


    registros_segmentados.append(
        {
            "id_incendio": incendio["id"],
            "segmento_id": segmento["segmento_id"],
            "rodovia": rodovia,
            "km": km,
            "data_hora_inicio": incendio["data_hora_inicio"],
            "data": pd.to_datetime(
                incendio["data_hora_inicio"]
            ).date(),
            "municipio": incendio["municipio"],
            "latitude": incendio["latitude"],
            "longitude": incendio["longitude"],
        }
    )


# ============================================================
# RESUMO DA SEGMENTAÇÃO
# ============================================================

print("\nResumo:")

print(f"Total analisado:        {len(incendios):,}")
print(f"Segmentados:            {len(registros_segmentados):,}")
print(f"Fora da área de estudo: {len(fora_area_estudo):,}")
print(f"Erros de segmentação:   {len(erros_segmentacao):,}")


# ============================================================
# MOSTRA REGISTROS FORA DA ÁREA
# ============================================================

if fora_area_estudo:

    print("\nRegistros fora da área de estudo:")

    df_fora = pd.DataFrame(fora_area_estudo)

    print(
        df_fora.to_string(index=False)
    )


# ============================================================
# INTERROMPE SOMENTE SE HOUVER ERRO REAL
# ============================================================

if erros_segmentacao:

    print("\nERROS DE SEGMENTAÇÃO:")

    df_erros = pd.DataFrame(erros_segmentacao)

    print(
        df_erros.to_string(index=False)
    )

    raise RuntimeError(
        "Existem incêndios dentro da área de estudo "
        "que não puderam ser associados a um segmento."
    )


# ============================================================
# PREPARA DATAFRAME
# ============================================================

df_insert = pd.DataFrame(
    registros_segmentados
)


if df_insert.empty:
    raise RuntimeError(
        "Nenhum incêndio foi segmentado."
    )


# ============================================================
# INSERE NO BANCO
# ============================================================

print(
    f"\nInserindo {len(df_insert):,} registros "
    "em tcc.incendios_segmentados..."
)


df_insert.to_sql(
    name="incendios_segmentados",
    schema="tcc",
    con=engine,
    if_exists="append",
    index=False,
    method="multi",
    chunksize=1000
)


# ============================================================
# CRIA GEOMETRIA
# ============================================================

with engine.begin() as conn:

    conn.execute(
        text("""
            UPDATE tcc.incendios_segmentados
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


print("\nResumo final por rodovia:")

print(
    resumo.to_string(index=False)
)


with engine.connect() as conn:

    total_final = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.incendios_segmentados;
        """)
    ).scalar()


print(f"\nTotal inserido: {total_final:,}")


print("\n" + "=" * 75)
print("PROCESSO CONCLUÍDO")
print("=" * 75)