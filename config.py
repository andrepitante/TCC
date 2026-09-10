from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DADOS_DIR = BASE_DIR / "dados"
MODELOS_DIR = BASE_DIR / "modelos_treinados"

ARQUIVO_INCENDIOS = (
    DADOS_DIR / "incendios" / "focos_de_incendio.xlsx"
)

ARQUIVO_RODOVIAS = (
    DADOS_DIR / "rodovias" / "export.geojson"
)

PASTA_METEOROLOGIA = (
    DADOS_DIR / "meteorologia"
)

# PostgreSQL
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "tcc_incendios"
DB_USER = "postgres"
DB_PASSWORD = "SUA_SENHA"

# Rodovias utilizadas no projeto
RODOVIAS = [
    "SP-021",
    "SP-280",
    "SP-300",
    "SP-330",
    "SP-348"
]

TAMANHO_SEGMENTO_KM = 5