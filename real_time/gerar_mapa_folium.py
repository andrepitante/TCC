# =============================================================================
# gerar_mapa_folium.py
#
# Gera mapa interativo dos scores de risco dos segmentos rodoviários.
#
# Uso:
#   python gerar_mapa_folium.py C:\TCC\results\risco_20250515_1400.csv
# =============================================================================

import sys
from pathlib import Path

import pandas as pd
import folium

from sqlalchemy import create_engine
from dotenv import load_dotenv

import os


# =============================================================================
# DIRETÓRIOS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RESULTS_DIR = BASE_DIR / "results"

load_dotenv(BASE_DIR / ".env")


# =============================================================================
# PARÂMETRO DE ENTRADA
# =============================================================================

if len(sys.argv) < 2:
    raise SystemExit(
        "\nUso:\n"
        "python gerar_mapa_folium.py "
        r"C:\TCC\results\risco_20250515_1400.csv"
    )

arquivo_csv = Path(sys.argv[1])

if not arquivo_csv.exists():
    raise SystemExit(
        f"\nArquivo CSV não encontrado:\n{arquivo_csv}"
    )


print()
print("=" * 80)
print("GERAÇÃO DO MAPA DE RISCO")
print("=" * 80)

print()
print("Arquivo de entrada:")
print(arquivo_csv)


# =============================================================================
# CARREGAR RESULTADOS DA MLP
# =============================================================================

resultado = pd.read_csv(arquivo_csv)

print()
print(f"Resultados carregados: {len(resultado)}")


colunas_obrigatorias = [
    "segmento_id",
    "rodovia",
    "score_risco",
    "nivel_risco"
]

faltantes = [
    coluna
    for coluna in colunas_obrigatorias
    if coluna not in resultado.columns
]

if faltantes:
    raise SystemExit(
        f"\nColunas ausentes no CSV: {faltantes}"
    )


# =============================================================================
# CONEXÃO COM POSTGRESQL
# =============================================================================

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


url_conexao = (
    f"postgresql+psycopg://"
    f"{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(url_conexao)


# =============================================================================
# CARREGAR POSIÇÃO DOS 332 SEGMENTOS
# =============================================================================

sql_posicoes = """
SELECT *
FROM tcc.segmentos_posicao
ORDER BY segmento_id
"""

posicoes = pd.read_sql(
    sql_posicoes,
    engine
)

print(f"Posições carregadas do banco: {len(posicoes)}")


# =============================================================================
# IDENTIFICAR COLUNAS DE LATITUDE / LONGITUDE
# =============================================================================

possiveis_lat = [
    "latitude",
    "lat",
    "latitude_mediana",
    "lat_mediana"
]

possiveis_lon = [
    "longitude",
    "lon",
    "lng",
    "longitude_mediana",
    "lon_mediana"
]


coluna_lat = next(
    (
        coluna
        for coluna in possiveis_lat
        if coluna in posicoes.columns
    ),
    None
)

coluna_lon = next(
    (
        coluna
        for coluna in possiveis_lon
        if coluna in posicoes.columns
    ),
    None
)


if coluna_lat is None or coluna_lon is None:

    print()
    print("Colunas encontradas em tcc.segmentos_posicao:")
    print(list(posicoes.columns))

    raise SystemExit(
        "\nNão foi possível identificar automaticamente "
        "latitude e longitude."
    )


print()
print(f"Latitude : {coluna_lat}")
print(f"Longitude: {coluna_lon}")


# =============================================================================
# UNIR SCORE + POSIÇÃO
# =============================================================================

dados = resultado.merge(
    posicoes[
        [
            "segmento_id",
            coluna_lat,
            coluna_lon
        ]
    ],
    on="segmento_id",
    how="left"
)


sem_posicao = dados[
    dados[coluna_lat].isna()
    |
    dados[coluna_lon].isna()
]


if len(sem_posicao) > 0:

    print()
    print("ATENÇÃO:")
    print(
        f"{len(sem_posicao)} segmentos sem posição."
    )

else:

    print()
    print("Todos os segmentos possuem posição.")


dados = dados.dropna(
    subset=[
        coluna_lat,
        coluna_lon
    ]
)


# =============================================================================
# CORES
# =============================================================================

def cor_risco(nivel):

    nivel = str(nivel).upper()

    if nivel == "BAIXO":
        return "green"

    if nivel == "MODERADO":
        return "yellow"

    if nivel == "ELEVADO":
        return "orange"

    if nivel == "MUITO ELEVADO":
        return "red"

    return "gray"


# =============================================================================
# DATA / HORA
# =============================================================================

if "hora_referencia" in dados.columns:

    hora_referencia = pd.to_datetime(
        dados["hora_referencia"].iloc[0]
    )

    texto_hora = hora_referencia.strftime(
        "%d/%m/%Y %H:%M"
    )

else:

    texto_hora = "Não informado"


# =============================================================================
# CRIAR MAPA
# =============================================================================

centro_lat = dados[coluna_lat].mean()
centro_lon = dados[coluna_lon].mean()


mapa = folium.Map(
    location=[
        centro_lat,
        centro_lon
    ],
    zoom_start=7,
    tiles=None,
    control_scale=True
)

folium.TileLayer(
    tiles=(
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
    ),
    attr="Esri",
    name="Esri World Topo Map",
    overlay=False,
    control=True
).add_to(mapa)

# =============================================================================
# ADICIONAR SEGMENTOS
# =============================================================================

for _, linha in dados.iterrows():

    score = float(
        linha["score_risco"]
    )

    nivel = linha["nivel_risco"]

    rodovia = linha["rodovia"]

    segmento = linha["segmento_id"]


    popup_html = f"""
    <div style="
        font-family: Arial;
        font-size: 14px;
        min-width: 230px;
    ">

        <b>Rodovia:</b>
        {rodovia}

        <br>

        <b>Segmento:</b>
        {segmento}

        <br><br>

        <b>Score de risco:</b>
        {score:.4f}

        <br>

        <b>Classificação:</b>
        {nivel}

        <br><br>

        <b>Hora de referência:</b>
        {texto_hora}

        <br>

        <b>Horizonte:</b>
        próximas 4 horas

    </div>
    """


# =============================================================================
# DESENHAR TRECHOS ENTRE OS SEGMENTOS
# =============================================================================

dados["numero_segmento"] = (
    dados["segmento_id"]
    .str.extract(r"SEG(\d+)", expand=False)
    .astype(int)
)

dados = dados.sort_values(
    ["rodovia", "numero_segmento"]
)

for rodovia, grupo in dados.groupby("rodovia"):

    grupo = grupo.sort_values("numero_segmento")

    registros = list(grupo.to_dict("records"))

    for i in range(len(registros) - 1):

        atual = registros[i]
        proximo = registros[i + 1]

        score = float(atual["score_risco"])
        nivel = atual["nivel_risco"]
        segmento = atual["segmento_id"]

        coordenadas = [
            [
                atual[coluna_lat],
                atual[coluna_lon]
            ],
            [
                proximo[coluna_lat],
                proximo[coluna_lon]
            ]
        ]

        popup_html = f"""
        <div style="
            font-family: Arial;
            font-size: 14px;
            min-width: 230px;
        ">

            <b>Rodovia:</b> {rodovia}<br>

            <b>Segmento:</b> {segmento}<br><br>

            <b>Score de risco:</b> {score:.4f}<br>

            <b>Classificação:</b> {nivel}<br><br>

            <b>Hora de referência:</b> {texto_hora}<br>

            <b>Horizonte:</b> próximas 4 horas

        </div>
        """

        folium.PolyLine(
            locations=coordenadas,
            color=cor_risco(nivel),
            weight=7,
            opacity=0.85,

            tooltip=(
                f"{rodovia} | "
                f"{segmento} | "
                f"{nivel} | "
                f"{score:.3f}"
            ),

            popup=folium.Popup(
                popup_html,
                max_width=350
            )

        ).add_to(mapa)
        
# =============================================================================
# CARREGAR ESTAÇÕES METEOROLÓGICAS
# =============================================================================

sql_estacoes = """
SELECT
    codigo_estacao,
    latitude,
    longitude
FROM tcc.estacoes_meteorologicas
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL
ORDER BY codigo_estacao
"""

estacoes = pd.read_sql(
    sql_estacoes,
    engine
)

print(f"Estações meteorológicas carregadas: {len(estacoes)}")

# =============================================================================
# CAMADA DAS ESTAÇÕES METEOROLÓGICAS
# =============================================================================

camada_estacoes = folium.FeatureGroup(
    name="Estações meteorológicas",
    show=True
)

for _, estacao in estacoes.iterrows():

    codigo = estacao["codigo_estacao"]

    folium.CircleMarker(
        location=[
            estacao["latitude"],
            estacao["longitude"]
        ],

        radius=5,

        color="#0066ff",
        weight=2,

        fill=True,
        fill_color="#0066ff",
        fill_opacity=0.90,

        tooltip=f"Estação {codigo}",

        popup=folium.Popup(
            f"""
            <div style="
                font-family: Arial;
                font-size: 14px;
                min-width: 180px;
            ">
                <b>Estação meteorológica</b><br><br>
                <b>Código:</b> {codigo}<br>
                <b>Latitude:</b> {estacao["latitude"]:.5f}<br>
                <b>Longitude:</b> {estacao["longitude"]:.5f}
            </div>
            """,
            max_width=250
        )
    ).add_to(camada_estacoes)

camada_estacoes.add_to(mapa)

# =============================================================================
# TÍTULO
# =============================================================================

titulo_html = f"""
<div style="
    position: fixed;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);

    z-index: 9999;

    background-color: white;

    padding: 10px 20px;

    border: 2px solid #444;

    border-radius: 6px;

    font-family: Arial;

    font-size: 18px;

    font-weight: bold;

    box-shadow: 0px 2px 6px rgba(0,0,0,0.3);
">

Risco estimado de incêndio nas próximas 4 horas

<br>

<div style="
    text-align:center;
    font-size:13px;
    font-weight:normal;
">

Hora de referência:
{texto_hora}

</div>

</div>
"""

mapa.get_root().html.add_child(
    folium.Element(titulo_html)
)


# =============================================================================
# LEGENDA
# =============================================================================

legenda_html = """
<div style="
    position: fixed;

    bottom: 40px;
    left: 40px;

    width: 190px;

    z-index: 9999;

    background-color: white;

    border: 2px solid #777;

    border-radius: 6px;

    padding: 10px;

    font-family: Arial;

    font-size: 13px;

    box-shadow: 0px 2px 6px rgba(0,0,0,0.3);
">

<b>Faixa operacional</b>

<br><br>

<span style="color:green;">●</span>
Baixo

<br>

<span style="color:#d4c900;">●</span>
Moderado

<br>

<span style="color:orange;">●</span>
Elevado

<br>

<span style="color:red;">●</span>
Muito elevado

</div>
"""

mapa.get_root().html.add_child(
    folium.Element(legenda_html)
)


# =============================================================================
# AJUSTAR ZOOM
# =============================================================================

mapa.fit_bounds(
    [
        [
            dados[coluna_lat].min(),
            dados[coluna_lon].min()
        ],
        [
            dados[coluna_lat].max(),
            dados[coluna_lon].max()
        ]
    ]
)


# =============================================================================
# NOME DO ARQUIVO
# =============================================================================

nome_csv = arquivo_csv.stem

if nome_csv.startswith("risco_"):

    identificador = nome_csv.replace(
        "risco_",
        ""
    )

else:

    identificador = nome_csv


arquivo_html = (
    RESULTS_DIR
    / f"mapa_risco_{identificador}.html"
)


folium.LayerControl(
    collapsed=False
).add_to(mapa)

# =============================================================================
# SALVAR
# =============================================================================

mapa.save(
    arquivo_html
)


print()
print("=" * 80)
print("MAPA GERADO")
print("=" * 80)

print()
print(f"Arquivo: {arquivo_html}")
print(f"Segmentos exibidos: {len(dados)}")

print()