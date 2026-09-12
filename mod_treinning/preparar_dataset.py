import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL


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


# =============================================================================
# FEATURES DO MODELO
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
# LEITURA DO DATASET
# =============================================================================

print("=" * 80)
print("PREPARAÇÃO DO DATASET PARA TREINAMENTO")
print("=" * 80)

sql = """
SELECT
    segmento_id,
    rodovia,
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

print("\nCarregando dados do PostgreSQL...")

df = pd.read_sql(sql, engine)

print(f"Linhas carregadas: {len(df):,}")


# =============================================================================
# TRATAMENTO DE NULL
# =============================================================================

antes = len(df)

df_modelo = df.dropna(
    subset=FEATURES + [TARGET]
).copy()

depois = len(df_modelo)

print()
print(f"Linhas antes do filtro : {antes:,}")
print(f"Linhas ignoradas       : {antes - depois:,}")
print(f"Linhas utilizáveis     : {depois:,}")


# =============================================================================
# DIVISÃO TEMPORAL COM PURGE DE 4 HORAS
# =============================================================================

df_modelo["hora_referencia"] = pd.to_datetime(
    df_modelo["hora_referencia"]
)

# -----------------------------------------------------------------------------
# TREINO
# Até 4 horas antes do início da validação.
# Isso impede que a janela-alvo de 4h atravesse para 2024.
# -----------------------------------------------------------------------------

treino = df_modelo[
    df_modelo["hora_referencia"] < "2023-12-31 20:00:00"
].copy()


# -----------------------------------------------------------------------------
# VALIDAÇÃO
# 2024, removendo as últimas 4 horas antes do conjunto de teste.
# -----------------------------------------------------------------------------

validacao = df_modelo[
    (df_modelo["hora_referencia"] >= "2024-01-01 00:00:00")
    & (df_modelo["hora_referencia"] < "2024-12-31 20:00:00")
].copy()


# -----------------------------------------------------------------------------
# TESTE
# 2025 em diante.
# -----------------------------------------------------------------------------

teste = df_modelo[
    df_modelo["hora_referencia"] >= "2025-01-01 00:00:00"
].copy()


# =============================================================================
# RESUMO
# =============================================================================

def resumo(nome, dados):

    positivas = int((dados[TARGET] == 1).sum())
    negativas = int((dados[TARGET] == 0).sum())

    print()
    print(nome)
    print("-" * 50)
    print(f"Total     : {len(dados):,}")
    print(f"Positivas : {positivas:,}")
    print(f"Negativas : {negativas:,}")

    if len(dados) > 0:
        print(
            f"Período   : {dados['hora_referencia'].min()} "
            f"até {dados['hora_referencia'].max()}"
        )


resumo("TREINO 2015-2023", treino)
resumo("VALIDAÇÃO 2024", validacao)
resumo("TESTE 2025-2026", teste)


# =============================================================================
# X E Y
# =============================================================================

X_train = treino[FEATURES].copy()
y_train = treino[TARGET].astype(int).copy()

X_val = validacao[FEATURES].copy()
y_val = validacao[TARGET].astype(int).copy()

X_test = teste[FEATURES].copy()
y_test = teste[TARGET].astype(int).copy()


# =============================================================================
# VALIDAÇÕES FINAIS
# =============================================================================

print()
print("=" * 80)
print("VALIDAÇÃO")
print("=" * 80)

print(f"\nQuantidade de features: {len(FEATURES)}")

print(f"NULLs X_train : {int(X_train.isna().sum().sum())}")
print(f"NULLs X_val   : {int(X_val.isna().sum().sum())}")
print(f"NULLs X_test  : {int(X_test.isna().sum().sum())}")

print()
print(f"X_train: {X_train.shape}")
print(f"X_val  : {X_val.shape}")
print(f"X_test : {X_test.shape}")

print()
print("PREPARAÇÃO CONCLUÍDA")