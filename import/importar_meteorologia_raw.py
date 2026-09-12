import os
import glob
import io
import pandas as pd
import psycopg

from dotenv import load_dotenv


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

PASTA_INMET = r"C:\TCC\data\INMET"

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# quantidade de linhas processadas por lote
CHUNK_SIZE = 25000


print("=" * 80)
print("IMPORTAÇÃO DOS DADOS METEOROLÓGICOS DO INMET")
print("=" * 80)


# ============================================================
# CONEXÃO
# ============================================================

conn = psycopg.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def converter_float(valor):

    if valor is None:
        return None

    valor = str(valor).strip()

    if (
        valor == ""
        or valor.lower() == "null"
        or valor.lower() == "nan"
    ):
        return None

    valor = valor.replace(",", ".")

    try:
        return float(valor)

    except ValueError:
        return None


def converter_data(valor):

    if not valor:
        return None

    try:
        return pd.to_datetime(valor).date()

    except Exception:
        return None


# ============================================================
# LÊ METADADOS DO ARQUIVO
# ============================================================

def ler_metadados(caminho):

    metadata = {}
    linha_cabecalho = None
    encoding_usado = None

    for encoding in ["utf-8", "latin-1"]:

        try:

            with open(
                caminho,
                "r",
                encoding=encoding,
                errors="strict"
            ) as arquivo:

                for numero_linha, linha in enumerate(arquivo):

                    linha = linha.strip()

                    if linha.startswith("Data Medicao;"):

                        linha_cabecalho = numero_linha
                        encoding_usado = encoding
                        break

                    if ":" in linha:

                        chave, valor = linha.split(":", 1)

                        metadata[
                            chave.strip()
                        ] = valor.strip()

            if linha_cabecalho is not None:
                break

        except UnicodeDecodeError:
            continue


    if linha_cabecalho is None:

        raise RuntimeError(
            f"Cabeçalho não encontrado em: {caminho}"
        )


    return (
        metadata,
        linha_cabecalho,
        encoding_usado
    )


# ============================================================
# INSERE / ATUALIZA ESTAÇÃO
# ============================================================

def salvar_estacao(
    cursor,
    metadata,
    arquivo
):

    codigo = metadata.get("Codigo Estacao")

    nome = metadata.get("Nome")

    latitude = converter_float(
        metadata.get("Latitude")
    )

    longitude = converter_float(
        metadata.get("Longitude")
    )

    altitude = converter_float(
        metadata.get("Altitude")
    )

    situacao = metadata.get("Situacao")

    data_inicial = converter_data(
        metadata.get("Data Inicial")
    )

    data_final = converter_data(
        metadata.get("Data Final")
    )

    periodicidade = metadata.get(
        "Periodicidade da Medicao"
    )


    if not codigo:

        raise RuntimeError(
            f"Código da estação não encontrado: {arquivo}"
        )


    if latitude is None or longitude is None:

        raise RuntimeError(
            f"Coordenadas inválidas da estação {codigo}"
        )


    cursor.execute(
        """
        INSERT INTO tcc.estacoes_meteorologicas
        (
            codigo_estacao,
            nome,
            latitude,
            longitude,
            altitude,
            situacao,
            data_inicial,
            data_final,
            periodicidade,
            arquivo_origem,
            geom
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,

            ST_SetSRID(
                ST_MakePoint(%s, %s),
                4326
            )
        )

        ON CONFLICT (codigo_estacao)

        DO UPDATE SET

            nome = EXCLUDED.nome,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            altitude = EXCLUDED.altitude,
            situacao = EXCLUDED.situacao,
            data_inicial = EXCLUDED.data_inicial,
            data_final = EXCLUDED.data_final,
            periodicidade = EXCLUDED.periodicidade,
            arquivo_origem = EXCLUDED.arquivo_origem,
            geom = EXCLUDED.geom;
        """,
        (
            codigo,
            nome,
            latitude,
            longitude,
            altitude,
            situacao,
            data_inicial,
            data_final,
            periodicidade,
            arquivo,

            longitude,
            latitude,
        )
    )


# ============================================================
# MAPA DAS COLUNAS DO INMET
# ============================================================

MAPA_COLUNAS = {

    "PRECIPITACAO TOTAL, HORARIO(mm)":
        "precipitacao",

    "PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA(mB)":
        "pressao_estacao",

    "PRESSAO ATMOSFERICA REDUZIDA NIVEL DO MAR, AUT(mB)":
        "pressao_nivel_mar",

    "PRESSAO ATMOSFERICA MAX.NA HORA ANT. (AUT)(mB)":
        "pressao_max",

    "PRESSAO ATMOSFERICA MIN. NA HORA ANT. (AUT)(mB)":
        "pressao_min",

    "RADIACAO GLOBAL(Kj/m²)":
        "radiacao_global",

    "TEMPERATURA DO AR - BULBO SECO, HORARIA(°C)":
        "temperatura",

    "TEMPERATURA DO PONTO DE ORVALHO(°C)":
        "temperatura_orvalho",

    "TEMPERATURA MAXIMA NA HORA ANT. (AUT)(°C)":
        "temperatura_max",

    "TEMPERATURA MINIMA NA HORA ANT. (AUT)(°C)":
        "temperatura_min",

    "TEMPERATURA ORVALHO MAX. NA HORA ANT. (AUT)(°C)":
        "temperatura_orvalho_max",

    "TEMPERATURA ORVALHO MIN. NA HORA ANT. (AUT)(°C)":
        "temperatura_orvalho_min",

    "UMIDADE REL. MAX. NA HORA ANT. (AUT)(%)":
        "umidade_max",

    "UMIDADE REL. MIN. NA HORA ANT. (AUT)(%)":
        "umidade_min",

    "UMIDADE RELATIVA DO AR, HORARIA(%)":
        "umidade",

    "VENTO, DIRECAO HORARIA (gr)(° (gr))":
        "vento_direcao",

    "VENTO, RAJADA MAXIMA(m/s)":
        "vento_rajada",

    "VENTO, VELOCIDADE HORARIA(m/s)":
        "vento_velocidade",
}


COLUNAS_BANCO = [

    "codigo_estacao",

    "data",
    "hora",
    "data_hora",

    "precipitacao",

    "pressao_estacao",
    "pressao_nivel_mar",
    "pressao_max",
    "pressao_min",

    "radiacao_global",

    "temperatura",
    "temperatura_orvalho",
    "temperatura_max",
    "temperatura_min",
    "temperatura_orvalho_max",
    "temperatura_orvalho_min",

    "umidade_max",
    "umidade_min",
    "umidade",

    "vento_direcao",
    "vento_rajada",
    "vento_velocidade",

    "arquivo_origem",
]


# ============================================================
# COPY POSTGRESQL
# ============================================================

def copiar_para_postgres(
    cursor,
    dataframe
):

    buffer = io.StringIO()

    dataframe.to_csv(
        buffer,
        index=False,
        header=False,
        na_rep="",
        date_format="%Y-%m-%d %H:%M:%S"
    )

    buffer.seek(0)


    comando = """
        COPY tcc.meteorologia_raw
        (
            codigo_estacao,

            data,
            hora,
            data_hora,

            precipitacao,

            pressao_estacao,
            pressao_nivel_mar,
            pressao_max,
            pressao_min,

            radiacao_global,

            temperatura,
            temperatura_orvalho,
            temperatura_max,
            temperatura_min,
            temperatura_orvalho_max,
            temperatura_orvalho_min,

            umidade_max,
            umidade_min,
            umidade,

            vento_direcao,
            vento_rajada,
            vento_velocidade,

            arquivo_origem
        )

        FROM STDIN

        WITH
        (
            FORMAT CSV,
            NULL ''
        );
    """


    with cursor.copy(comando) as copy:

        copy.write(
            buffer.getvalue()
        )


# ============================================================
# LOCALIZA ARQUIVOS
# ============================================================

arquivos = sorted(
    glob.glob(
        os.path.join(
            PASTA_INMET,
            #"dados_A716_H_*.csv"
            "dados_*_H_*.csv"
        )
    )
)


print(f"\nArquivos encontrados: {len(arquivos):,}")


if not arquivos:

    raise RuntimeError(
        "Nenhum arquivo horário do INMET encontrado."
    )


# ============================================================
# PROCESSA ARQUIVOS
# ============================================================

total_importado = 0


try:

    with conn.cursor() as cursor:

        for numero, caminho in enumerate(
            arquivos,
            start=1
        ):

            arquivo_nome = os.path.basename(
                caminho
            )


            print("\n" + "-" * 80)

            print(
                f"[{numero}/{len(arquivos)}] "
                f"{arquivo_nome}"
            )


            metadata, linha_cabecalho, encoding = (
                ler_metadados(caminho)
            )


            codigo_estacao = metadata.get(
                "Codigo Estacao"
            )


            print(
                f"Estação: "
                f"{codigo_estacao} - "
                f"{metadata.get('Nome')}"
            )


            # ------------------------------------------------
            # VERIFICA SE JÁ EXISTEM DADOS
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM tcc.meteorologia_raw
                WHERE codigo_estacao = %s;
                """,
                (codigo_estacao,)
            )

            existentes = cursor.fetchone()[0]


            if existentes > 0:

                print(
                    f"ATENÇÃO: estação {codigo_estacao} "
                    f"já possui {existentes:,} registros."
                )

                print(
                    "Arquivo ignorado para evitar duplicação."
                )

                continue


            # ------------------------------------------------
            # ESTAÇÃO
            # ------------------------------------------------

            salvar_estacao(
                cursor,
                metadata,
                arquivo_nome
            )

            conn.commit()


            # ------------------------------------------------
            # LEITURA EM LOTES
            # ------------------------------------------------

            registros_estacao = 0


            leitor = pd.read_csv(
                caminho,

                sep=";",

                skiprows=linha_cabecalho,

                encoding=encoding,

                dtype=str,

                na_values=[
                    "null",
                    "NULL",
                    "Null",
                    ""
                ],

                keep_default_na=True,

                chunksize=CHUNK_SIZE
            )


            for numero_chunk, df in enumerate(
                leitor,
                start=1
            ):

                # remove colunas completamente vazias
                df = df.dropna(
                    axis=1,
                    how="all"
                )


                # --------------------------------------------
                # VALIDA COLUNAS FUNDAMENTAIS
                # --------------------------------------------

                if "Data Medicao" not in df.columns:

                    raise RuntimeError(
                        f"'Data Medicao' não encontrada "
                        f"em {arquivo_nome}"
                    )


                if "Hora Medicao" not in df.columns:

                    raise RuntimeError(
                        f"'Hora Medicao' não encontrada "
                        f"em {arquivo_nome}"
                    )


                # --------------------------------------------
                # DATA
                # --------------------------------------------

                df_saida = pd.DataFrame(index=df.index)

                df_saida["codigo_estacao"] = codigo_estacao
                
                if df_saida["codigo_estacao"].isna().any():
                    raise RuntimeError(
                        f"Código da estação ficou nulo durante o processamento de {arquivo_nome}"
                    )
                

                df_saida["data"] = pd.to_datetime(
                    df["Data Medicao"],
                    errors="coerce"
                )


                # --------------------------------------------
                # HORA
                # --------------------------------------------

                horas = (
                    df["Hora Medicao"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .str.zfill(4)
                )


                horas_formatadas = (
                    horas.str[0:2]
                    + ":"
                    + horas.str[2:4]
                    + ":00"
                )


                df_saida["hora"] = (
                    horas_formatadas
                )


                # --------------------------------------------
                # DATA / HORA
                # --------------------------------------------

                df_saida["data_hora"] = (
                    pd.to_datetime(
                        df["Data Medicao"]
                        + " "
                        + horas_formatadas,
                        errors="coerce"
                    )
                )


                # --------------------------------------------
                # VARIÁVEIS METEOROLÓGICAS
                # --------------------------------------------

                for coluna_inmet, coluna_banco in (
                    MAPA_COLUNAS.items()
                ):

                    if coluna_inmet in df.columns:

                        df_saida[coluna_banco] = (
                            pd.to_numeric(
                                df[coluna_inmet]
                                .str.replace(
                                    ",",
                                    ".",
                                    regex=False
                                ),
                                errors="coerce"
                            )
                        )

                    else:

                        df_saida[
                            coluna_banco
                        ] = None


                # --------------------------------------------
                # ARQUIVO ORIGEM
                # --------------------------------------------

                df_saida[
                    "arquivo_origem"
                ] = arquivo_nome


                # --------------------------------------------
                # REMOVE DATA/HORA INVÁLIDA
                # --------------------------------------------

                invalidas = (
                    df_saida[
                        "data_hora"
                    ].isna().sum()
                )


                if invalidas > 0:

                    print(
                        f"  Aviso: {invalidas} "
                        "linhas com data/hora inválida."
                    )


                    df_saida = df_saida[
                        df_saida[
                            "data_hora"
                        ].notna()
                    ].copy()


                # --------------------------------------------
                # GARANTE ORDEM
                # --------------------------------------------

                df_saida = df_saida[
                    COLUNAS_BANCO
                ]


                # --------------------------------------------
                # COPY
                # --------------------------------------------

                copiar_para_postgres(
                    cursor,
                    df_saida
                )


                conn.commit()


                quantidade = len(
                    df_saida
                )


                registros_estacao += (
                    quantidade
                )

                total_importado += (
                    quantidade
                )


                print(
                    f"  Lote {numero_chunk}: "
                    f"{quantidade:,} registros "
                    f"| estação: "
                    f"{registros_estacao:,}"
                )


            print(
                f"OK: {codigo_estacao} "
                f"→ {registros_estacao:,} "
                "registros importados."
            )


# ============================================================
# ERRO
# ============================================================

except Exception as erro:

    conn.rollback()

    print("\nERRO DURANTE A IMPORTAÇÃO:")

    print(erro)

    raise


finally:

    conn.close()


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 80)

print(
    f"TOTAL IMPORTADO: "
    f"{total_importado:,} registros"
)

print("IMPORTAÇÃO CONCLUÍDA")

print("=" * 80)