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
# FAIXAS DEFINIDAS PARA AS RODOVIAS
# ============================================================

rodovias = {
    "SP-021": (0, 135),
    "SP-280": (10, 320),
    "SP-300": (60, 670),
    "SP-330": (10, 450),
    "SP-348": (10, 175),
}


# ============================================================
# GERAR SEGMENTOS DE 5 KM
# ============================================================

segmentos = []

for rodovia, (km_inicio_rodovia, km_fim_rodovia) in rodovias.items():

    numero_segmento = 1
    rodovia_id = rodovia.replace("-", "")

    for km_inicio in range(km_inicio_rodovia, km_fim_rodovia, 5):

        km_fim = km_inicio + 5

        segmento_id = (
            f"{rodovia_id}_SEG{numero_segmento:03d}"
        )

        segmentos.append({
            "segmento_id": segmento_id,
            "rodovia": rodovia,
            "numero_segmento": numero_segmento,
            "km_inicio": float(km_inicio),
            "km_fim": float(km_fim),
        })

        numero_segmento += 1


df = pd.DataFrame(segmentos)


# ============================================================
# RESUMO
# ============================================================

print("=" * 75)
print("CRIAÇÃO DOS SEGMENTOS DE RODOVIAS")
print("=" * 75)

print(f"\nTotal de segmentos gerados: {len(df)}")

print("\nQuantidade por rodovia:")

print(
    df.groupby("rodovia")
    .size()
    .to_string()
)

print("\nPrimeiros segmentos:")

print(
    df.head(15)
    .to_string(index=False)
)


# ============================================================
# VERIFICAR SE A TABELA EXISTE
# ============================================================

with engine.connect() as conn:

    existe = conn.execute(
        text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'tcc'
              AND table_name = 'segmentos_rodovias'
        );
        """)
    ).scalar()

if not existe:
    raise RuntimeError(
        "A tabela tcc.segmentos_rodovias não existe. "
        "Execute primeiro o SQL de criação da tabela."
    )


# ============================================================
# VERIFICAR SE A TABELA ESTÁ VAZIA
# ============================================================

with engine.connect() as conn:

    quantidade_atual = conn.execute(
        text("""
        SELECT COUNT(*)
        FROM tcc.segmentos_rodovias;
        """)
    ).scalar()

print(f"\nRegistros atualmente na tabela: {quantidade_atual}")


if quantidade_atual > 0:
    print("\nATENÇÃO:")
    print(
        "A tabela já possui registros. "
        "O script foi interrompido para evitar duplicação."
    )

    print("\nNenhum dado foi inserido.")

else:

    # ========================================================
    # INSERIR SEGMENTOS
    # ========================================================

    df.to_sql(
        "segmentos_rodovias",
        engine,
        schema="tcc",
        if_exists="append",
        index=False,
    )

    print("\nSegmentos inseridos com sucesso.")


# ============================================================
# VALIDAÇÃO FINAL
# ============================================================

with engine.connect() as conn:

    resultado = pd.read_sql(
        """
        SELECT
            rodovia,
            COUNT(*) AS segmentos,
            MIN(km_inicio) AS km_min,
            MAX(km_fim) AS km_max
        FROM tcc.segmentos_rodovias
        GROUP BY rodovia
        ORDER BY rodovia;
        """,
        conn
    )


print("\nResumo da tabela:")

print(
    resultado.to_string(index=False)
)


print("\n" + "=" * 75)
print("PROCESSO CONCLUÍDO")
print("=" * 75)