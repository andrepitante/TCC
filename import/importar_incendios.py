from pathlib import Path
import os

import pandas as pd
import psycopg
from dotenv import load_dotenv


# ============================================================
# CAMINHOS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

load_dotenv(ROOT / ".env")

ARQUIVO = (
    ROOT
    / "data"
    / "incendios"
    / "focos_de_incendio_base_publico.xlsx"
)


# ============================================================
# CONEXÃO COM POSTGRESQL
# ============================================================

def conectar():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


# ============================================================
# CONVERSÃO DE NaN / NaT PARA NULL
# ============================================================

def limpar_valor(valor):
    if pd.isna(valor):
        return None
    return valor


# ============================================================
# PRINCIPAL
# ============================================================

def main():

    print("=" * 70)
    print("IMPORTAÇÃO DA BASE HISTÓRICA DE INCÊNDIOS")
    print("=" * 70)

    print(f"\nArquivo:")
    print(ARQUIVO)

    if not ARQUIVO.exists():
        raise FileNotFoundError(
            f"\nArquivo não encontrado:\n{ARQUIVO}"
        )

    # --------------------------------------------------------
    # LEITURA DO EXCEL
    # --------------------------------------------------------

    print("\nLendo arquivo Excel...")

    df = pd.read_excel(ARQUIVO)

    print(f"\nRegistros encontrados : {len(df):,}")
    print(f"Colunas encontradas   : {len(df.columns)}")

    print("\nColunas do arquivo:")

    for coluna in df.columns:
        print(f"  - {coluna}")

    # --------------------------------------------------------
    # MAPEAMENTO DAS COLUNAS
    # --------------------------------------------------------

    mapa_colunas = {
        "CONCESSIONÁRIA": "concessionaria",
        "DATA E HORA INÍCIO": "data_hora_inicio",
        "DATA E HORA FIM": "data_hora_fim",
        "N° OCORRENCIA": "numero_ocorrencia",
        "RODOVIA": "rodovia",
        "MUNICÍPIO": "municipio",
        "REG_ADM_SP": "reg_adm_sp",
        "KM": "km",
        "SENTIDO": "sentido",
        "LATITUDE": "latitude",
        "LONGITUDE": "longitude",
        "EXTENSÃO": "extensao",
        "PROPORÇÃO": "proporcao",
        "LOCAL ORIGEM": "local_origem",
        "FAIXA DE DOMÍNIO": "faixa_dominio",
        "DATA INICIO": "data_inicio",
        "ID_HORA": "id_hora",
        "RODOVIA_KM": "rodovia_km",
        "RODOVIA_KM E SENTIDO": "rodovia_km_sentido"
    }

    # --------------------------------------------------------
    # VERIFICAR SE TODAS AS COLUNAS EXISTEM
    # --------------------------------------------------------

    faltantes = [
        coluna
        for coluna in mapa_colunas
        if coluna not in df.columns
    ]

    if faltantes:

        print("\nERRO: colunas esperadas não foram encontradas:")

        for coluna in faltantes:
            print(f"  - {coluna}")

        raise ValueError(
            "Estrutura do Excel diferente da esperada."
        )

    print("\nTodas as colunas esperadas foram encontradas.")

    # --------------------------------------------------------
    # SELECIONAR E RENOMEAR
    # --------------------------------------------------------

    df = df[list(mapa_colunas.keys())]

    df = df.rename(columns=mapa_colunas)

    # --------------------------------------------------------
    # CONVERSÃO DE DATAS
    # --------------------------------------------------------

    print("\nConvertendo campos de data...")

    df["data_hora_inicio"] = pd.to_datetime(
        df["data_hora_inicio"],
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce"
    )

    df["data_hora_fim"] = pd.to_datetime(
        df["data_hora_fim"],
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce"
    )

    df["data_inicio"] = pd.to_datetime(
        df["data_inicio"],
        dayfirst=True,
        errors="coerce"
    ).dt.date
    
    
    # --------------------------------------------------------
    # CONVERSÃO NUMÉRICA
    # --------------------------------------------------------

    print("Convertendo campos numéricos...")

    for coluna in [
        "km",
        "latitude",
        "longitude"
    ]:
        df[coluna] = pd.to_numeric(
            df[coluna],
            errors="coerce"
        )

    # --------------------------------------------------------
    # DIAGNÓSTICO
    # --------------------------------------------------------

    print("\nResumo antes da importação:")

    print(
        f"Coordenadas completas: "
        f"{df[['latitude', 'longitude']].dropna().shape[0]:,}"
    )

    print(
        f"Sem latitude: "
        f"{df['latitude'].isna().sum():,}"
    )

    print(
        f"Sem longitude: "
        f"{df['longitude'].isna().sum():,}"
    )

    print(
        f"Sem data inicial: "
        f"{df['data_hora_inicio'].isna().sum():,}"
    )

    # --------------------------------------------------------
    # CONECTAR AO BANCO
    # --------------------------------------------------------

    print("\nConectando ao PostgreSQL...")

    with conectar() as conn:

        with conn.cursor() as cur:

            print("Conexão realizada.")

            print(
                "\nLimpando tcc.incendios_raw "
                "antes da nova carga..."
            )

            cur.execute("""
                TRUNCATE TABLE tcc.incendios_raw
                RESTART IDENTITY;
            """)

            # ------------------------------------------------
            # SQL DE INSERÇÃO
            # ------------------------------------------------

            sql = """
                INSERT INTO tcc.incendios_raw
                (
                    concessionaria,
                    data_hora_inicio,
                    data_hora_fim,
                    numero_ocorrencia,
                    rodovia,
                    municipio,
                    reg_adm_sp,
                    km,
                    sentido,
                    latitude,
                    longitude,
                    extensao,
                    proporcao,
                    local_origem,
                    faixa_dominio,
                    data_inicio,
                    id_hora,
                    rodovia_km,
                    rodovia_km_sentido,
                    geom
                )
                VALUES
                (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s,

                    ST_SetSRID(
                        ST_MakePoint(
                            %s::double precision,
                            %s::double precision
                        ),
                        4326
                    )
                );
            """
            
                        
            print("\nIniciando importação...")

            total = len(df)

            for indice, row in df.iterrows():

                # ----------------------------------------------------
                # Coordenadas
                # ----------------------------------------------------

                latitude = limpar_valor(row["latitude"])
                longitude = limpar_valor(row["longitude"])

                # Se as duas coordenadas existirem, marcamos como válido
                if latitude is not None and longitude is not None:
                    tem_coordenada = True
                else:
                    tem_coordenada = None

                # ----------------------------------------------------
                # Valores enviados ao PostgreSQL
                # ----------------------------------------------------

                valores = (
                    limpar_valor(row["concessionaria"]),
                    limpar_valor(row["data_hora_inicio"]),
                    limpar_valor(row["data_hora_fim"]),
                    limpar_valor(row["numero_ocorrencia"]),

                    limpar_valor(row["rodovia"]),
                    limpar_valor(row["municipio"]),
                    limpar_valor(row["reg_adm_sp"]),

                    limpar_valor(row["km"]),
                    limpar_valor(row["sentido"]),

                    latitude,
                    longitude,

                    limpar_valor(row["extensao"]),
                    limpar_valor(row["proporcao"]),
                    limpar_valor(row["local_origem"]),
                    limpar_valor(row["faixa_dominio"]),

                    limpar_valor(row["data_inicio"]),
                    limpar_valor(row["id_hora"]),

                    limpar_valor(row["rodovia_km"]),
                    limpar_valor(row["rodovia_km_sentido"]),

                    longitude,
                    latitude
                )
                
                
                # ----------------------------------------------------
                # Inserir no PostgreSQL
                # ----------------------------------------------------

                cur.execute(sql, valores)

                contador = indice + 1

                if contador % 5000 == 0:
                    print(
                        f"  {contador:,} / "
                        f"{total:,} registros"
                )
            
            
        conn.commit()

    # --------------------------------------------------------
    # VALIDAÇÃO FINAL
    # --------------------------------------------------------

    print("\nValidando dados gravados...")

    with conectar() as conn:

        with conn.cursor() as cur:

            cur.execute("""
                SELECT COUNT(*)
                FROM tcc.incendios_raw;
            """)

            quantidade = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*)
                FROM tcc.incendios_raw
                WHERE geom IS NOT NULL;
            """)

            georreferenciados = cur.fetchone()[0]

    print("\n" + "=" * 70)
    print("IMPORTAÇÃO CONCLUÍDA")
    print("=" * 70)

    print(f"Excel           : {len(df):,}")
    print(f"Banco           : {quantidade:,}")
    print(f"Georreferenciados: {georreferenciados:,}")

    if quantidade == len(df):
        print("\nOK - quantidade importada confere com o Excel.")
    else:
        print("\nATENÇÃO - quantidade divergente!")


if __name__ == "__main__":
    main()