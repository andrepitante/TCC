from pathlib import Path
import os
import json

import joblib
import pandas as pd
import tensorflow as tf

from sqlalchemy import create_engine
from dotenv import load_dotenv


# =============================================================================
# CAMINHOS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_MODELO = BASE_DIR / "model"

ARQUIVO_MODELO = PASTA_MODELO / "mlp_risco_incendio_v1.keras"
ARQUIVO_SCALER = PASTA_MODELO / "scaler_mlp_v1.pkl"
ARQUIVO_METADATA = PASTA_MODELO / "mlp_risco_incendio_v1.json"


# =============================================================================
# BANCO DE DADOS
# =============================================================================

load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = (
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL)


# =============================================================================
# CARREGAR MLP V1
# =============================================================================

print("=" * 80)
print("CARREGANDO MLP V1")
print("=" * 80)

modelo = tf.keras.models.load_model(ARQUIVO_MODELO)

scaler = joblib.load(ARQUIVO_SCALER)

with open(
    ARQUIVO_METADATA,
    "r",
    encoding="utf-8"
) as arquivo:
    metadados = json.load(arquivo)

FEATURES = metadados["features"]

print("Modelo       : OK")
print("Scaler       : OK")
print("Metadados    : OK")
print("Features     :", len(FEATURES))
print(
    "Horizonte    :",
    metadados["horizonte_horas"],
    "horas"
)


# =============================================================================
# BUSCAR UMA AMOSTRA REAL DO BANCO
# =============================================================================

print()
print("=" * 80)
print("BUSCANDO AMOSTRA NO POSTGRESQL")
print("=" * 80)

query = """
SELECT *
FROM tcc.dataset_modelo
WHERE hora_referencia >= '2025-01-01'
ORDER BY hora_referencia
LIMIT 1
"""

amostra = pd.read_sql(
    query,
    engine
)

if amostra.empty:
    raise RuntimeError(
        "Nenhuma amostra encontrada."
    )

print("Amostra encontrada.")


# =============================================================================
# PREPARAR DADOS
# =============================================================================

segmento_id = amostra.loc[
    0,
    "segmento_id"
]

rodovia = amostra.loc[
    0,
    "rodovia"
]

hora_referencia = amostra.loc[
    0,
    "hora_referencia"
]

valor_real = int(
    amostra.loc[
        0,
        "incendio_proximas_4h"
    ]
)

X = amostra[
    FEATURES
].astype(float)

if X.isnull().any().any():
    raise RuntimeError(
        "A amostra possui valores meteorológicos NULL."
    )


# =============================================================================
# NORMALIZAÇÃO
# =============================================================================

X_scaled = scaler.transform(X)


# =============================================================================
# INFERÊNCIA
# =============================================================================

score = float(
    modelo.predict(
        X_scaled,
        verbose=0
    )[0][0]
)


# =============================================================================
# CLASSIFICAÇÃO OPERACIONAL
# =============================================================================

if score < 0.15:

    nivel = "BAIXO"

elif score < 0.25:

    nivel = "MODERADO"

elif score < 0.40:

    nivel = "ELEVADO"

else:

    nivel = "MUITO ELEVADO"


# =============================================================================
# RESULTADO
# =============================================================================

print()
print("=" * 80)
print("RESULTADO DA INFERÊNCIA")
print("=" * 80)

print()
print(
    "Segmento       :",
    segmento_id
)

print(
    "Rodovia        :",
    rodovia
)

print(
    "Hora referência:",
    hora_referencia
)

print(
    f"Score MLP      : {score:.4f}"
)

print(
    "Nível de risco :",
    nivel
)

print(
    "Horizonte      : próximas",
    metadados["horizonte_horas"],
    "horas"
)

print(
    "Real histórico :",
    valor_real
)

print()
print("=" * 80)
print("INFERÊNCIA CONCLUÍDA")
print("=" * 80)