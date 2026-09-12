import os
import json
import joblib
import numpy as np
from pathlib import Path

import pandas as pd
import tensorflow as tf

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME"),
)

engine = create_engine(url)

tf.random.set_seed(42)


# =============================================================================
# FEATURES
# =============================================================================

FEATURES = [
    "temperatura_atual",
    "umidade_atual",
    "precipitacao_atual",
    "vento_atual",
    "rajada_atual",

    "temperatura_media_24h",
    "temperatura_max_24h",
    "umidade_media_24h",
    "umidade_min_24h",
    "vento_medio_24h",
    "rajada_max_24h",

    "chuva_24h",
    "horas_com_chuva_24h",

    "chuva_72h",
    "horas_com_chuva_72h",

    "chuva_168h",
    "horas_sem_chuva_ate_168h",
]

TARGET = "incendio_proximas_4h"


# =============================================================================
# LEITURA DOS DADOS
# =============================================================================

print("=" * 80)
print("TREINAMENTO MLP - RISCO DE INCÊNDIO NAS PRÓXIMAS 4 HORAS")
print("=" * 80)

sql = """
SELECT
    hora_referencia,

    temperatura_atual,
    umidade_atual,
    precipitacao_atual,
    vento_atual,
    rajada_atual,

    temperatura_media_24h,
    temperatura_max_24h,
    umidade_media_24h,
    umidade_min_24h,
    vento_medio_24h,
    rajada_max_24h,

    chuva_24h,
    horas_com_chuva_24h,

    chuva_72h,
    horas_com_chuva_72h,

    chuva_168h,
    horas_sem_chuva_ate_168h,

    incendio_proximas_4h

FROM tcc.dataset_modelo

ORDER BY hora_referencia;
"""

print("\nCarregando dataset...")

df = pd.read_sql(sql, engine)

df = df.dropna(
    subset=FEATURES + [TARGET]
).copy()

df["hora_referencia"] = pd.to_datetime(
    df["hora_referencia"]
)

print(f"Linhas utilizáveis: {len(df):,}")


# =============================================================================
# DIVISÃO TEMPORAL
# =============================================================================

treino = df[
    df["hora_referencia"] < "2023-12-31 20:00:00"
].copy()

validacao = df[
    (df["hora_referencia"] >= "2024-01-01 00:00:00")
    & (df["hora_referencia"] < "2024-12-31 20:00:00")
].copy()

teste = df[
    df["hora_referencia"] >= "2025-01-01 00:00:00"
].copy()


X_train = treino[FEATURES]
y_train = treino[TARGET].astype(int)

X_val = validacao[FEATURES]
y_val = validacao[TARGET].astype(int)

X_test = teste[FEATURES]
y_test = teste[TARGET].astype(int)


print()
print(f"Treino    : {X_train.shape}")
print(f"Validação : {X_val.shape}")
print(f"Teste     : {X_test.shape}")


# =============================================================================
# NORMALIZAÇÃO
# =============================================================================

print("\nAplicando StandardScaler...")

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)


# =============================================================================
# MODELO MLP
# =============================================================================

modelo = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(len(FEATURES),)),

    tf.keras.layers.Dense(
        32,
        activation="relu"
    ),

    tf.keras.layers.Dropout(
        0.20
    ),

    tf.keras.layers.Dense(
        16,
        activation="relu"
    ),

    tf.keras.layers.Dense(
        8,
        activation="relu"
    ),

    tf.keras.layers.Dense(
        1,
        activation="sigmoid"
    ),
])


modelo.compile(
    optimizer=tf.keras.optimizers.Adam(
        learning_rate=0.001
    ),

    loss="binary_crossentropy",

    metrics=[
        tf.keras.metrics.BinaryAccuracy(
            name="accuracy"
        ),

        tf.keras.metrics.Precision(
            name="precision"
        ),

        tf.keras.metrics.Recall(
            name="recall"
        ),

        tf.keras.metrics.AUC(
            name="auc"
        ),
    ],
)


print()
print("=" * 80)
print("ARQUITETURA DA REDE")
print("=" * 80)

modelo.summary()


# =============================================================================
# EARLY STOPPING
# =============================================================================

early_stopping = tf.keras.callbacks.EarlyStopping(
    monitor="val_auc",
    mode="max",
    patience=5,
    restore_best_weights=True,
    verbose=1,
)


# =============================================================================
# TREINAMENTO
# =============================================================================

print()
print("=" * 80)
print("INICIANDO TREINAMENTO")
print("=" * 80)

historico = modelo.fit(

    X_train_scaled,
    y_train,

    validation_data=(
        X_val_scaled,
        y_val
    ),

    epochs=50,

    batch_size=256,

    callbacks=[
        early_stopping
    ],

    verbose=1,
)


# =============================================================================
# AVALIAÇÃO
# =============================================================================

def avaliar(nome, X, y, threshold=0.5):

    prob = modelo.predict(
        X,
        verbose=0
    ).ravel()

    pred = (
        prob >= threshold
    ).astype(int)

    accuracy = accuracy_score(
        y,
        pred
    )

    precision = precision_score(
        y,
        pred
    )

    recall = recall_score(
        y,
        pred
    )

    f1 = f1_score(
        y,
        pred
    )

    auc = roc_auc_score(
        y,
        prob
    )

    matriz = confusion_matrix(
        y,
        pred
    )

    print()
    print("=" * 80)
    print(nome)
    print("=" * 80)

    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1-score : {f1:.4f}")
    print(f"ROC-AUC  : {auc:.4f}")

    print()
    print("Matriz de confusão:")
    print(matriz)
    
# =============================================================================
# ANÁLISE DE THRESHOLDS NA VALIDAÇÃO
# =============================================================================

print()
print("=" * 80)
print("ANÁLISE DE THRESHOLDS - VALIDAÇÃO 2024")
print("=" * 80)

prob_val = modelo.predict(
    X_val_scaled,
    verbose=0
).ravel()

thresholds = [
    0.50,
    0.45,
    0.40,
    0.35,
    0.30,
    0.25,
    0.20,
    0.15,
    0.10,
]

for threshold in thresholds:

    pred_val = (
        prob_val >= threshold
    ).astype(int)

    precision = precision_score(
        y_val,
        pred_val,
        zero_division=0
    )

    recall = recall_score(
        y_val,
        pred_val,
        zero_division=0
    )

    f1 = f1_score(
        y_val,
        pred_val,
        zero_division=0
    )

    matriz = confusion_matrix(
        y_val,
        pred_val
    )

    tn, fp, fn, tp = matriz.ravel()

    print()
    print(f"Threshold: {threshold:.2f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1-score : {f1:.4f}")
    print(f"TP       : {tp:,}")
    print(f"FP       : {fp:,}")
    print(f"FN       : {fn:,}")
    print(f"TN       : {tn:,}")

avaliar(
    "VALIDAÇÃO 2024",
    X_val_scaled,
    y_val,
)

avaliar(
    "TESTE 2025-2026 - THRESHOLD 0.25",
    X_test_scaled,
    y_test,
    threshold=0.25
)

# =============================================================================
# ANÁLISE OPERACIONAL POR FAIXAS DE RISCO
# =============================================================================

print()
print("=" * 80)
print("ANÁLISE POR FAIXAS DE RISCO - TESTE 2025-2026")
print("=" * 80)

prob_test = modelo.predict(
    X_test_scaled,
    verbose=0
).ravel()

resultado = teste[
    ["hora_referencia"]
].copy()

resultado["score_risco"] = prob_test
resultado["incendio_real"] = y_test.to_numpy()


# -----------------------------------------------------------------------------
# Faixas provisórias de risco
# -----------------------------------------------------------------------------

resultado["nivel_risco"] = np.select(

    [
        resultado["score_risco"] < 0.15,

        (resultado["score_risco"] >= 0.15)
        & (resultado["score_risco"] < 0.25),

        (resultado["score_risco"] >= 0.25)
        & (resultado["score_risco"] < 0.40),

        resultado["score_risco"] >= 0.40,
    ],

    [
        "BAIXO",
        "MODERADO",
        "ELEVADO",
        "MUITO ELEVADO",
    ],

    default="INDEFINIDO",
)


# -----------------------------------------------------------------------------
# Resumo das faixas
# -----------------------------------------------------------------------------

ordem = [
    "BAIXO",
    "MODERADO",
    "ELEVADO",
    "MUITO ELEVADO",
]

for nivel in ordem:

    faixa = resultado[
        resultado["nivel_risco"] == nivel
    ]

    total = len(faixa)

    incendios = int(
        faixa["incendio_real"].sum()
    )

    if total > 0:
        taxa = incendios / total
    else:
        taxa = 0

    print()
    print(f"Nível             : {nivel}")
    print(f"Amostras          : {total:,}")
    print(f"Positivas reais   : {incendios:,}")
    print(f"Frequência real   : {taxa:.2%}")

# =============================================================================
# SALVAR MODELO V1
# =============================================================================

PASTA_MODELO = BASE_DIR / "model"
PASTA_MODELO.mkdir(exist_ok=True)

# Rede neural
modelo.save(
    PASTA_MODELO / "mlp_risco_incendio_v1.keras"
)

# StandardScaler
joblib.dump(
    scaler,
    PASTA_MODELO / "scaler_mlp_v1.pkl"
)

# Metadados necessários para utilizar o modelo posteriormente
metadados = {
    "versao": "v1",
    "horizonte_horas": 4,
    "features": FEATURES,

    "faixas_risco": {
        "baixo": [0.00, 0.15],
        "moderado": [0.15, 0.25],
        "elevado": [0.25, 0.40],
        "muito_elevado": [0.40, 1.00]
    },

    "treino": "2015-2023",
    "validacao": "2024",
    "teste": "2025-2026"
}

with open(
    PASTA_MODELO / "mlp_risco_incendio_v1.json",
    "w",
    encoding="utf-8"
) as arquivo:

    json.dump(
        metadados,
        arquivo,
        indent=4,
        ensure_ascii=False
    )

print()
print("Modelo salvo:")
print(PASTA_MODELO / "mlp_risco_incendio_v1.keras")

print("Scaler salvo:")
print(PASTA_MODELO / "scaler_mlp_v1.pkl")

print("Metadados salvos:")
print(PASTA_MODELO / "mlp_risco_incendio_v1.json")

print()
print("=" * 80)
print("TREINAMENTO CONCLUÍDO")
print("=" * 80)