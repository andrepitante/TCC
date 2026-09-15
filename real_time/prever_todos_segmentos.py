from datetime import datetime
from pathlib import Path
import os
import subprocess
import sys
import json
import joblib
import tensorflow as tf
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv


# =============================================================================
# HORÁRIO DE REFERÊNCIA
# =============================================================================

print("=" * 80)
print("PREVISÃO DE RISCO - TODOS OS SEGMENTOS")
print("=" * 80)

print()
print("Formato esperado: AAAA-MM-DD HH:MM")
print("Exemplo        : 2025-08-15 14:00")
print()

entrada = input(
    "Informe o horário de referência: "
).strip()

try:
    hora_referencia = datetime.strptime(
        entrada,
        "%Y-%m-%d %H:%M"
    )

except ValueError:

    print()
    print("ERRO: data/hora inválida.")
    print(
        "Use o formato AAAA-MM-DD HH:MM"
    )

    raise SystemExit(1)


# A base trabalha em resolução horária.
# Portanto, somente horas fechadas serão aceitas.

if hora_referencia.minute != 0:

    print()
    print(
        "ERRO: informe uma hora fechada, "
        "por exemplo 14:00."
    )

    raise SystemExit(1)


print()
print("Horário selecionado:")
print(
    hora_referencia.strftime(
        "%d/%m/%Y %H:%M"
    )
)

print()
print(
    "Horizonte da previsão:",
    hora_referencia.strftime(
        "%d/%m/%Y %H:%M"
    ),
    "até",
    (
        hora_referencia
    ).strftime(
        "%d/%m/%Y %H:%M"
    ),
    "+ 4 horas"
)

# =============================================================================
# CONEXÃO COM O POSTGRESQL
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

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
# PREPARAR CACHE METEOROLÓGICO
# =============================================================================

print()
print("=" * 80)
print("PREPARANDO CACHE METEOROLÓGICO")
print("=" * 80)

script_preparacao = (
    BASE_DIR
    / "real_time"
    / "preparar_meteorologia.py"
)

hora_parametro = hora_referencia.strftime(
    "%Y-%m-%d %H:%M"
)

resultado_preparacao = subprocess.run(
    [
        sys.executable,
        str(script_preparacao),
        hora_parametro
    ],
    check=False
)

if resultado_preparacao.returncode != 0:

    print()
    print(
        "ERRO: preparação meteorológica falhou."
    )

    raise SystemExit(
        resultado_preparacao.returncode
    )

print()
print(
    "Cache meteorológico preparado com sucesso."
)

# =============================================================================
# CARREGAR SEGMENTOS
# =============================================================================

print()
print("=" * 80)
print("CARREGANDO SEGMENTOS RODOVIÁRIOS")
print("=" * 80)

query = """
SELECT
    segmento_id,
    rodovia,
    km_inicio,
    km_fim
FROM tcc.segmentos_rodovias
ORDER BY
    rodovia,
    km_inicio
"""

segmentos = pd.read_sql(
    query,
    engine
)

print()
print(
    "Segmentos encontrados:",
    len(segmentos)
)

print()
print(
    segmentos.groupby("rodovia")
    .size()
    .to_string()
)

# =============================================================================
# VERIFICAR METEOROLOGIA NO HORÁRIO DE REFERÊNCIA
# =============================================================================

print()
print("=" * 80)
print("VERIFICANDO METEOROLOGIA DO HORÁRIO")
print("=" * 80)

query_meteo = """
SELECT
    segmento_id,
    data_hora,
    temperatura,
    umidade,
    precipitacao,
    vento,
    rajada
FROM tcc.meteorologia_segmentos_horaria
WHERE data_hora = %(hora_referencia)s
ORDER BY segmento_id
"""

meteorologia = pd.read_sql(
    query_meteo,
    engine,
    params={
        "hora_referencia": hora_referencia
    }
)

print()
print(
    "Segmentos com registro meteorológico:",
    meteorologia["segmento_id"].nunique()
)

print()
print("Disponibilidade das variáveis:")

for coluna in [
    "temperatura",
    "umidade",
    "precipitacao",
    "vento",
    "rajada"
]:
    quantidade = meteorologia[coluna].notna().sum()

    print(
        f"{coluna:15s}: "
        f"{quantidade:3d} / {len(segmentos)}"
    )
    
    # =============================================================================
# IDENTIFICAR SEGMENTOS AUSENTES NO CACHE
# =============================================================================

segmentos_cache = set(
    meteorologia["segmento_id"]
)

segmentos_total = set(
    segmentos["segmento_id"]
)

segmentos_faltantes = sorted(
    segmentos_total - segmentos_cache
)

print()
print("=" * 80)
print("SEGMENTOS AUSENTES NO CACHE")
print("=" * 80)

print()
print(
    "Total de segmentos:",
    len(segmentos_total)
)

print(
    "Presentes no cache:",
    len(segmentos_cache)
)

print(
    "Ausentes no cache:",
    len(segmentos_faltantes)
)

print()

if segmentos_faltantes:
    print("Primeiros segmentos ausentes:")

    for segmento in segmentos_faltantes[:20]:
        print(" -", segmento)

else:
    print(
        "Todos os segmentos possuem "
        "meteorologia no horário."
    )
    
    # =============================================================================
# TESTE DE RECONSTRUÇÃO DE METEOROLOGIA
# =============================================================================

if segmentos_faltantes:

    segmento_teste = segmentos_faltantes[0]

    print()
    print("=" * 80)
    print("TESTE DE RECONSTRUÇÃO DA METEOROLOGIA")
    print("=" * 80)

    print()
    print("Segmento de teste:", segmento_teste)

    query_teste = """
    SELECT
        se.segmento_id,
        se.codigo_estacao,
        se.distancia_km,
        se.ranking,
        m.data_hora,
        m.temperatura,
        m.umidade,
        m.precipitacao,
        m.vento_velocidade AS vento,
        m.vento_rajada AS rajada
    FROM tcc.segmentos_estacoes se
    LEFT JOIN tcc.meteorologia_raw m
        ON m.codigo_estacao = se.codigo_estacao
        AND m.data_hora = %(hora_referencia)s
    WHERE se.segmento_id = %(segmento_id)s
        AND se.distancia_km <= 100
    ORDER BY se.ranking
    """

    teste_estacoes = pd.read_sql(
        query_teste,
        engine,
        params={
            "segmento_id": segmento_teste,
            "hora_referencia": hora_referencia
        }
    )

    print()
    print(
        teste_estacoes[
            [
                "codigo_estacao",
                "distancia_km",
                "ranking",
                "temperatura",
                "umidade",
                "precipitacao",
                "vento",
                "rajada"
            ]
        ].head(10).to_string(
            index=False
        )
    )
    
# =============================================================================
# GERAR FEATURES DOS 332 SEGMENTOS
# =============================================================================

print()
print("=" * 80)
print("GERANDO FEATURES PARA A MLP")
print("=" * 80)

query_features = """
SELECT
    s.segmento_id,
    s.rodovia,

    MAX(m.temperatura)
        FILTER (WHERE m.data_hora = %(hora)s)
        AS temperatura_atual,

    MAX(m.umidade)
        FILTER (WHERE m.data_hora = %(hora)s)
        AS umidade_atual,

    MAX(m.precipitacao)
        FILTER (WHERE m.data_hora = %(hora)s)
        AS precipitacao_atual,

    MAX(m.vento)
        FILTER (WHERE m.data_hora = %(hora)s)
        AS vento_atual,

    MAX(m.rajada)
        FILTER (WHERE m.data_hora = %(hora)s)
        AS rajada_atual,

    AVG(m.temperatura)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '24 hours'
        )
        AS temperatura_media_24h,

    MAX(m.temperatura)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '24 hours'
        )
        AS temperatura_max_24h,

    AVG(m.umidade)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '24 hours'
        )
        AS umidade_media_24h,

    MIN(m.umidade)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '24 hours'
        )
        AS umidade_min_24h,

    AVG(m.vento)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '24 hours'
        )
        AS vento_medio_24h,

    MAX(m.rajada)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '24 hours'
        )
        AS rajada_max_24h,

    SUM(m.precipitacao)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '24 hours'
        )
        AS chuva_24h,

    COUNT(*)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '24 hours'
              AND m.precipitacao > 0
        )
        AS horas_com_chuva_24h,

    SUM(m.precipitacao)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '72 hours'
        )
        AS chuva_72h,

    COUNT(*)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '72 hours'
              AND m.precipitacao > 0
        )
        AS horas_com_chuva_72h,

    SUM(m.precipitacao)
        FILTER (
            WHERE m.data_hora > %(hora)s::timestamp - interval '168 hours'
        )
        AS chuva_168h,

    CASE
        WHEN MAX(m.data_hora)
             FILTER (WHERE m.precipitacao > 0) IS NULL
        THEN 168

        ELSE LEAST(
            168,
            EXTRACT(
                EPOCH FROM (
                    %(hora)s::timestamp
                    -
                    MAX(m.data_hora)
                    FILTER (WHERE m.precipitacao > 0)
                )
            ) / 3600
        )
    END AS horas_sem_chuva_ate_168h

FROM tcc.segmentos_rodovias s

JOIN tcc.meteorologia_segmentos_horaria m
    ON m.segmento_id = s.segmento_id

WHERE m.data_hora > %(hora)s::timestamp - interval '168 hours'
  AND m.data_hora <= %(hora)s::timestamp

GROUP BY
    s.segmento_id,
    s.rodovia

ORDER BY
    s.rodovia,
    s.segmento_id
"""

print()
print("=" * 80)
print("DEBUG DA HORA USADA NAS FEATURES")
print("=" * 80)

print("hora_referencia =", repr(hora_referencia))
print("tipo            =", type(hora_referencia))

features = pd.read_sql(
    query_features,
    engine,
    params={
        "hora": hora_referencia
    }
)

print()
print("DEBUG precipitação atual:")
print(
    features[
        [
            "segmento_id",
            "precipitacao_atual",
            "chuva_24h",
            "chuva_72h",
            "chuva_168h"
        ]
    ]
    .sort_values(
        "precipitacao_atual",
        ascending=False
    )
    .head(10)
    .to_string(index=False)
)





print()
print(
    "Segmentos processados:",
    len(features)
)

print(
    "Quantidade de features:",
    len(features.columns) - 2
)

print()
print(
    features.head().to_string(
        index=False
    )
)

# =============================================================================
# CARREGAR E VALIDAR MLP V1
# =============================================================================

print()
print("=" * 80)
print("CARREGANDO E VALIDANDO MLP V1")
print("=" * 80)

PASTA_MODELO = BASE_DIR / "model"

ARQUIVO_MODELO = (
    PASTA_MODELO / "mlp_risco_incendio_v1.keras"
)

ARQUIVO_SCALER = (
    PASTA_MODELO / "scaler_mlp_v1.pkl"
)

ARQUIVO_METADATA = (
    PASTA_MODELO / "mlp_risco_incendio_v1.json"
)

modelo = tf.keras.models.load_model(
    ARQUIVO_MODELO
)

scaler = joblib.load(
    ARQUIVO_SCALER
)

with open(
    ARQUIVO_METADATA,
    "r",
    encoding="utf-8"
) as arquivo:

    metadados = json.load(arquivo)


# =============================================================================
# VALIDAR FEATURES
# =============================================================================

features_modelo = metadados["features"]

features_geradas = [
    coluna
    for coluna in features.columns
    if coluna not in [
        "segmento_id",
        "rodovia"
    ]
]

print()
print(
    "Features esperadas:",
    len(features_modelo)
)

print(
    "Features geradas  :",
    len(features_geradas)
)

if features_geradas != features_modelo:

    print()
    print(
        "ERRO: as features geradas não correspondem "
        "às features utilizadas no treinamento."
    )

    print()
    print("Esperadas:")
    print(features_modelo)

    print()
    print("Geradas:")
    print(features_geradas)

    raise SystemExit(1)

print()
print(
    "Validação das features: OK"
)


# =============================================================================
# VERIFICAR VALORES NULOS
# =============================================================================

qtd_nulos = int(
    features[features_modelo]
    .isnull()
    .sum()
    .sum()
)

print(
    "Valores NULL          :",
    qtd_nulos
)

if qtd_nulos > 0:

    print()
    print(
        "ERRO: existem valores NULL nas features."
    )
    
    print()
    print("=" * 80)
    print("DIAGNÓSTICO DE VALORES NULL")
    print("=" * 80)

    linhas_com_null = features[
        features[features_modelo]
        .isnull()
        .any(axis=1)
    ]

    for _, linha in linhas_com_null.iterrows():

        print()
        print(
            "Segmento:",
            linha["segmento_id"]
        )

        print(
            "Rodovia  :",
            linha["rodovia"]
        )

        print("Features NULL:")

        for coluna in features_modelo:

            if pd.isna(linha[coluna]):
                print(" -", coluna)

    raise SystemExit(1)


# =============================================================================
# PREPARAR ENTRADA DA MLP
# =============================================================================

X = features[
    features_modelo
].astype(float)

X_scaled = scaler.transform(X)


# =============================================================================
# PREVISÃO DOS 332 SEGMENTOS
# =============================================================================

print()
print("=" * 80)
print("CALCULANDO SCORES DE RISCO")
print("=" * 80)

scores = modelo.predict(
    X_scaled,
    verbose=0
).ravel()

features["score_risco"] = scores


# =============================================================================
# FAIXAS OPERACIONAIS
# =============================================================================

def classificar_risco(score):

    if score < 0.20:
        return "BAIXO"

    if score < 0.35:
        return "MODERADO"

    if score < 0.42:
        return "ELEVADO"

    return "MUITO ELEVADO"


features["nivel_risco"] = (
    features["score_risco"]
    .apply(classificar_risco)
)


# =============================================================================
# RESULTADO
# =============================================================================

resultado = features[
    [
        "segmento_id",
        "rodovia",
        "score_risco",
        "nivel_risco"
    ]
].copy()

resultado = resultado.sort_values(
    "score_risco",
    ascending=False
)

print()
print(
    "Segmentos avaliados:",
    len(resultado)
)

print()
print(
    "Score mínimo:",
    f"{resultado['score_risco'].min():.4f}"
)

print(
    "Score médio :",
    f"{resultado['score_risco'].mean():.4f}"
)

print(
    "Score máximo:",
    f"{resultado['score_risco'].max():.4f}"
)

print()
print("Distribuição por nível:")

print(
    resultado["nivel_risco"]
    .value_counts()
    .to_string()
)

print()
print("10 segmentos com maior score:")

print(
    resultado.head(10)
    .to_string(
        index=False
    )
)

# =============================================================================
# DIAGNÓSTICO DA VARIAÇÃO DAS FEATURES
# =============================================================================

print()
print("=" * 80)
print("DIAGNÓSTICO DAS FEATURES")
print("=" * 80)

qtd_perfis = (
    features[features_modelo]
    .drop_duplicates()
    .shape[0]
)

qtd_scores = (
    resultado["score_risco"]
    .round(6)
    .nunique()
)

print()
print(
    "Perfis meteorológicos distintos:",
    qtd_perfis
)

print(
    "Scores distintos             :",
    qtd_scores
)

print()
print("Variação por feature:")

for coluna in features_modelo:

    print(
        f"{coluna:30s} "
        f"min={features[coluna].min():8.2f} "
        f"max={features[coluna].max():8.2f} "
        f"únicos={features[coluna].nunique():3d}"
    )
    
# =============================================================================
# EXPORTAÇÃO DOS RESULTADOS
# =============================================================================

RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

timestamp_arquivo = hora_referencia.strftime("%Y%m%d_%H%M")

resultado_exportacao = resultado.copy()

# Hora utilizada para gerar a previsão
resultado_exportacao["hora_referencia"] = hora_referencia

# Horizonte definido no projeto
resultado_exportacao["horizonte_horas"] = 4


# -----------------------------------------------------------------------------
# Arquivos de saída
# -----------------------------------------------------------------------------

arquivo_csv = RESULTS_DIR / f"risco_{timestamp_arquivo}.csv"
arquivo_json = RESULTS_DIR / f"risco_{timestamp_arquivo}.json"


# -----------------------------------------------------------------------------
# CSV
# -----------------------------------------------------------------------------

resultado_exportacao.to_csv(
    arquivo_csv,
    index=False,
    encoding="utf-8-sig"
)


# -----------------------------------------------------------------------------
# JSON
# -----------------------------------------------------------------------------

resultado_exportacao.to_json(
    arquivo_json,
    orient="records",
    force_ascii=False,
    indent=2,
    date_format="iso"
)


# -----------------------------------------------------------------------------
# Confirmação
# -----------------------------------------------------------------------------

print()
print("=" * 80)
print("RESULTADOS EXPORTADOS")
print("=" * 80)

print(f"CSV : {arquivo_csv}")
print(f"JSON: {arquivo_json}")
print(f"Registros exportados: {len(resultado_exportacao)}")


# =============================================================================
# GERAR MAPA FOLIUM
# =============================================================================

script_mapa = BASE_DIR / "real_time" / "gerar_mapa_folium.py"

print()
print("=" * 80)
print("GERANDO MAPA FOLIUM")
print("=" * 80)

resultado_mapa = subprocess.run(
    [
        sys.executable,
        str(script_mapa),
        str(arquivo_csv)
    ],
    check=False
)

if resultado_mapa.returncode != 0:
    print()
    print("ATENÇÃO: houve erro na geração do mapa.")
else:
    print()
    print("Mapa gerado com sucesso.")