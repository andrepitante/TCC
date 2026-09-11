import os
import math

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
# ============================================================

sql = """
SELECT
    rodovia,
    km
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


df = pd.read_sql(sql, engine)


# ============================================================
# NORMALIZAÇÃO
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
# ANÁLISE
# ============================================================

print("=" * 75)
print("ANÁLISE DA COBERTURA DOS SEGMENTOS DE 5 KM")
print("=" * 75)


for rodovia, dados in df.groupby("rodovia"):

    km_min = dados["km"].min()
    km_max = dados["km"].max()

    inicio = math.floor(km_min / 5) * 5
    fim = math.ceil(km_max / 5) * 5

    # Se o máximo cair exatamente em múltiplo de 5,
    # precisamos ainda incluir esse ponto no segmento seguinte.
    if km_max == fim:
        fim += 5

    segmentos = []

    atual = inicio

    while atual < fim:

        seguinte = atual + 5

        quantidade = (
            (dados["km"] >= atual)
            & (dados["km"] < seguinte)
        ).sum()

        segmentos.append({
            "rodovia": rodovia,
            "km_inicio": atual,
            "km_fim": seguinte,
            "incendios": int(quantidade),
        })

        atual = seguinte

    resultado = pd.DataFrame(segmentos)

    print("\n" + "=" * 75)
    print(rodovia)
    print("=" * 75)

    print(f"KM mínimo observado : {km_min}")
    print(f"KM máximo observado : {km_max}")
    print(f"Faixa analisada      : {inicio} até {fim}")
    print(f"Segmentos possíveis  : {len(resultado)}")

    com_incendio = (resultado["incendios"] > 0).sum()
    sem_incendio = (resultado["incendios"] == 0).sum()

    print(f"Com incêndio         : {com_incendio}")
    print(f"Sem incêndio         : {sem_incendio}")

    print("\nSegmentos sem nenhum incêndio histórico:")

    vazios = resultado[
        resultado["incendios"] == 0
    ]

    if vazios.empty:
        print("Nenhum.")
    else:
        print(
            vazios[
                ["km_inicio", "km_fim"]
            ].to_string(index=False)
        )

    print("\nSegmentos das extremidades:")

    print(
        pd.concat([
            resultado.head(3),
            resultado.tail(3)
        ])
        .drop_duplicates()
        .to_string(index=False)
    )


print("\n" + "=" * 75)
print("ANÁLISE CONCLUÍDA")
print("=" * 75)