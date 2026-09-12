import os
import glob
import pandas as pd


# ============================================================
# CONFIGURAÇÃO
# ============================================================

PASTA_INMET = r"C:\TCC\data\INMET"


print("=" * 80)
print("ANÁLISE DOS ARQUIVOS METEOROLÓGICOS DO INMET")
print("=" * 80)


# ============================================================
# LOCALIZA CSVs
# ============================================================

arquivos = glob.glob(
    os.path.join(
        PASTA_INMET,
        "**",
        "*.csv"
    ),
    recursive=True
)


print(f"\nArquivos CSV encontrados: {len(arquivos):,}")

if not arquivos:
    raise RuntimeError(
        f"Nenhum CSV encontrado em {PASTA_INMET}"
    )


# ============================================================
# FUNÇÃO PARA LER METADADOS
# ============================================================

def ler_metadados(caminho):

    metadata = {}

    # INMET normalmente usa UTF-8 ou Latin-1.
    # Primeiro tentamos UTF-8.
    try:
        encoding = "utf-8"

        with open(
            caminho,
            "r",
            encoding=encoding,
            errors="strict"
        ) as arquivo:
            linhas = [
                arquivo.readline().strip()
                for _ in range(15)
            ]

    except UnicodeDecodeError:

        encoding = "latin-1"

        with open(
            caminho,
            "r",
            encoding=encoding,
            errors="replace"
        ) as arquivo:
            linhas = [
                arquivo.readline().strip()
                for _ in range(15)
            ]

    linha_cabecalho = None

    for indice, linha in enumerate(linhas):

        if linha.startswith("Data Medicao;"):
            linha_cabecalho = indice
            break

        if ":" in linha:

            chave, valor = linha.split(":", 1)

            metadata[
                chave.strip()
            ] = valor.strip()


    return metadata, linha_cabecalho, encoding


# ============================================================
# ANALISA CADA ARQUIVO
# ============================================================

resultado = []


for numero, caminho in enumerate(arquivos, start=1):

    nome_arquivo = os.path.basename(caminho)

    print(
        f"[{numero}/{len(arquivos)}] "
        f"{nome_arquivo}"
    )

    try:

        metadata, linha_cabecalho, encoding = ler_metadados(
            caminho
        )

        if linha_cabecalho is None:

            resultado.append(
                {
                    "arquivo": nome_arquivo,
                    "status": "CABECALHO_NAO_ENCONTRADO"
                }
            )

            continue


        # quantidade de linhas de dados
        with open(
            caminho,
            "r",
            encoding=encoding,
            errors="replace"
        ) as arquivo:

            total_linhas = sum(
                1
                for _ in arquivo
            )


        qtd_registros = (
            total_linhas
            - linha_cabecalho
            - 1
        )


        resultado.append(
            {
                "arquivo": nome_arquivo,

                "estacao": metadata.get(
                    "Codigo Estacao"
                ),

                "nome": metadata.get(
                    "Nome"
                ),

                "latitude": metadata.get(
                    "Latitude"
                ),

                "longitude": metadata.get(
                    "Longitude"
                ),

                "altitude": metadata.get(
                    "Altitude"
                ),

                "situacao": metadata.get(
                    "Situacao"
                ),

                "data_inicial": metadata.get(
                    "Data Inicial"
                ),

                "data_final": metadata.get(
                    "Data Final"
                ),

                "periodicidade": metadata.get(
                    "Periodicidade da Medicao"
                ),

                "qtd_registros": qtd_registros,

                "encoding": encoding,

                "linha_cabecalho": linha_cabecalho,

                "status": "OK",
            }
        )

    except Exception as erro:

        resultado.append(
            {
                "arquivo": nome_arquivo,
                "status": f"ERRO: {erro}"
            }
        )


# ============================================================
# DATAFRAME
# ============================================================

df = pd.DataFrame(resultado)


print("\n" + "=" * 80)
print("RESUMO")
print("=" * 80)


ok = df[df["status"] == "OK"]

print(f"\nArquivos válidos: {len(ok):,}")
print(
    f"Arquivos com problema: "
    f"{len(df) - len(ok):,}"
)


if not ok.empty:

    print(
        f"Estações distintas: "
        f"{ok['estacao'].nunique():,}"
    )


# ============================================================
# LISTA DAS ESTAÇÕES
# ============================================================

if not ok.empty:

    colunas = [
        "estacao",
        "nome",
        "latitude",
        "longitude",
        "altitude",
        "situacao",
        "data_inicial",
        "data_final",
        "periodicidade",
        "qtd_registros"
    ]

    print("\nEstações encontradas:")

    print(
        ok[colunas]
        .sort_values(
            [
                "estacao",
                "data_inicial"
            ]
        )
        .to_string(index=False)
    )


# ============================================================
# PROBLEMAS
# ============================================================

problemas = df[
    df["status"] != "OK"
]


if not problemas.empty:

    print("\nArquivos com problema:")

    print(
        problemas[
            [
                "arquivo",
                "status"
            ]
        ].to_string(index=False)
    )


# ============================================================
# DUPLICIDADE DE ESTAÇÃO
# ============================================================

if not ok.empty:

    arquivos_por_estacao = (
        ok.groupby("estacao")
        .size()
        .reset_index(
            name="arquivos"
        )
        .sort_values(
            "arquivos",
            ascending=False
        )
    )

    duplicadas = arquivos_por_estacao[
        arquivos_por_estacao["arquivos"] > 1
    ]

    print(
        "\nEstações presentes em mais "
        "de um arquivo:"
    )

    if duplicadas.empty:

        print("Nenhuma.")

    else:

        print(
            duplicadas.to_string(
                index=False
            )
        )


# ============================================================
# SALVA RELATÓRIO
# ============================================================

saida = os.path.join(
    PASTA_INMET,
    "relatorio_arquivos_inmet.csv"
)


df.to_csv(
    saida,
    sep=";",
    index=False,
    encoding="utf-8-sig"
)


print(
    f"\nRelatório salvo em:\n{saida}"
)


print("\n" + "=" * 80)
print("ANÁLISE CONCLUÍDA")
print("=" * 80)