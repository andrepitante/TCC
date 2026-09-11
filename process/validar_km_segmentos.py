import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()

engine = create_engine(
    f"postgresql+psycopg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)


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

print("=" * 70)
print("VALIDAÇÃO DOS QUILÔMETROS")
print("=" * 70)

df = pd.read_sql(sql, engine)

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


for rodovia, dados in df.groupby("rodovia"):

    print("\n" + "=" * 70)
    print(rodovia)
    print("=" * 70)

    print(f"Registros : {len(dados):,}")
    print(f"KM mínimo : {dados['km'].min()}")
    print(f"KM máximo : {dados['km'].max()}")
    print(f"KM médio  : {dados['km'].mean():.2f}")
    print(f"Mediana   : {dados['km'].median():.2f}")

    print("\n10 menores:")
    print(
        dados["km"]
        .sort_values()
        .head(10)
        .to_string(index=False)
    )

    print("\n10 maiores:")
    print(
        dados["km"]
        .sort_values(ascending=False)
        .head(10)
        .to_string(index=False)
    )


print("\n" + "=" * 70)
print("VALIDAÇÃO CONCLUÍDA")
print("=" * 70)