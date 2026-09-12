from pathlib import Path
import json
import joblib
import numpy as np
import tensorflow as tf


# =============================================================================
# CAMINHOS DO PROJETO
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_MODELO = BASE_DIR / "model"

ARQUIVO_MODELO = PASTA_MODELO / "mlp_risco_incendio_v1.keras"
ARQUIVO_SCALER = PASTA_MODELO / "scaler_mlp_v1.pkl"
ARQUIVO_METADATA = PASTA_MODELO / "mlp_risco_incendio_v1.json"


# =============================================================================
# CARREGAR MODELO
# =============================================================================

print("=" * 80)
print("CARREGANDO MODELO DE RISCO")
print("=" * 80)

modelo = tf.keras.models.load_model(ARQUIVO_MODELO)
scaler = joblib.load(ARQUIVO_SCALER)

with open(
    ARQUIVO_METADATA,
    "r",
    encoding="utf-8"
) as arquivo:
    metadados = json.load(arquivo)

print()
print("Modelo carregado:")
print(ARQUIVO_MODELO)

print()
print("Scaler carregado:")
print(ARQUIVO_SCALER)

print()
print("Metadados carregados:")
print(ARQUIVO_METADATA)

print()
print("Versão:", metadados["versao"])
print("Horizonte:", metadados["horizonte_horas"], "horas")

print()
print("Features esperadas:")

for i, feature in enumerate(
    metadados["features"],
    start=1
):
    print(f"{i:02d} - {feature}")