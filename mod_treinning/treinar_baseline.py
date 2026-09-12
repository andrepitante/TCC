import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
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
# LEITURA
# =============================================================================

print("=" * 80)
print("BASELINE - REGRESSÃO LOGÍSTICA")
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

df = pd.read_sql(sql, engine)

df = df.dropna(
    subset=FEATURES + [TARGET]
).copy()

df["hora_referencia"] = pd.to_datetime(
    df["hora_referencia"]
)


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


# =============================================================================
# NORMALIZAÇÃO
# =============================================================================

print("\nAjustando StandardScaler somente no treino...")

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)


# =============================================================================
# MODELO
# =============================================================================

print("Treinando Regressão Logística...")

modelo = LogisticRegression(
    max_iter=1000,
    class_weight=None,
    random_state=42,
)

modelo.fit(
    X_train_scaled,
    y_train,
)


# =============================================================================
# AVALIAÇÃO
# =============================================================================

def avaliar(nome, X, y):

    pred = modelo.predict(X)
    prob = modelo.predict_proba(X)[:, 1]

    accuracy = accuracy_score(y, pred)
    precision = precision_score(y, pred)
    recall = recall_score(y, pred)
    f1 = f1_score(y, pred)
    auc = roc_auc_score(y, prob)

    matriz = confusion_matrix(y, pred)

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


avaliar(
    "VALIDAÇÃO 2024",
    X_val_scaled,
    y_val,
)

avaliar(
    "TESTE 2025-2026",
    X_test_scaled,
    y_test,
)

print()
print("=" * 80)
print("BASELINE CONCLUÍDO")
print("=" * 80)