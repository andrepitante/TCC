from pathlib import Path
import json
import os

import geopandas as gpd
import pandas as pd
import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv


# ============================================================
# CAMINHOS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

load_dotenv(ROOT / ".env")

ARQUIVO = (
    ROOT
    / "data"
    / "rodovias"
    / "export.geojson"
)


# ============================================================
# CONEXÃO
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
# LIMPEZA
# ============================================================

def limpar_valor(valor):
    if valor is None:
        return None

    try:
        if pd.isna(valor):
            return None
    except Exception:
        pass

    return str(valor)


# ============================================================
# PRINCIPAL
# ============================================================

def main():

    print("=" * 70)
    print("IMPORTAÇÃO DAS RODOVIAS OSM")
    print("=" * 70)

    print(f"\nArquivo:")
    print(ARQUIVO)

    if not ARQUIVO.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado:\n{ARQUIVO}"
        )

    # --------------------------------------------------------
    # LEITURA
    # --------------------------------------------------------

    print("\nLendo GeoJSON...")

    gdf = gpd.read_file(ARQUIVO)

    print(f"\nFeatures encontradas : {len(gdf):,}")
    print(f"CRS informado        : {gdf.crs}")

    print("\nTipos de geometria:")

    print(
        gdf.geometry
        .geom_type
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # CRS
    # --------------------------------------------------------

    if gdf.crs is None:
        print("\nCRS ausente.")
        print("Definindo EPSG:4326...")
        gdf = gdf.set_crs("EPSG:4326")

    elif gdf.crs.to_epsg() != 4326:
        print("\nConvertendo geometria para EPSG:4326...")
        gdf = gdf.to_crs("EPSG:4326")

    # --------------------------------------------------------
    # DIAGNÓSTICO DAS RODOVIAS
    # --------------------------------------------------------

    print("\nReferências das cinco rodovias:")

    if "ref" in gdf.columns:

        for codigo in [
            "SP-021",
            "SP-280",
            "SP-300",
            "SP-330",
            "SP-348"
        ]:

            quantidade = (
                gdf["ref"]
                .fillna("")
                .astype(str)
                .str.contains(codigo, regex=False)
                .sum()
            )

            print(
                f"  {codigo}: "
                f"{quantidade:,} features"
            )

    # --------------------------------------------------------
    # CONEXÃO
    # --------------------------------------------------------

    print("\nConectando ao PostgreSQL...")

    with conectar() as conn:

        with conn.cursor() as cur:

            print("Conexão realizada.")

            print(
                "\nLimpando tcc.rodovias_osm_raw "
                "antes da nova carga..."
            )

            cur.execute("""
                TRUNCATE TABLE
                tcc.rodovias_osm_raw
                RESTART IDENTITY;
            """)

            sql = """
                INSERT INTO tcc.rodovias_osm_raw
                (
                    osm_id,
                    ref,
                    nome,
                    highway,
                    surface,
                    maxspeed,
                    lanes,
                    oneway,
                    bridge,
                    carriageway_ref,
                    atributos,
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
                    %s,
                    ST_SetSRID(
                        ST_GeomFromGeoJSON(%s),
                        4326
                    )
                );
            """

            print("\nIniciando importação...")

            total = len(gdf)

            for indice, row in gdf.iterrows():

                # ------------------------------------------------
                # TODAS AS PROPRIEDADES ORIGINAIS
                # ------------------------------------------------

                atributos = {}

                for coluna in gdf.columns:

                    if coluna == "geometry":
                        continue

                    valor = row[coluna]

                    if valor is None:
                        continue

                    try:
                        if pd.isna(valor):
                            continue
                    except Exception:
                        pass

                    atributos[coluna] = str(valor)

                # ------------------------------------------------
                # GEOMETRIA
                # ------------------------------------------------

                geometria = row.geometry

                if geometria is None or geometria.is_empty:
                    geojson_geom = None
                else:
                    geojson_geom = json.dumps(
                        geometria.__geo_interface__
                    )

                # ------------------------------------------------
                # INSERÇÃO
                # ------------------------------------------------

                valores = (
                    limpar_valor(
                        row["@id"]
                        if "@id" in gdf.columns
                        else None
                    ),

                    limpar_valor(
                        row["ref"]
                        if "ref" in gdf.columns
                        else None
                    ),

                    limpar_valor(
                        row["name"]
                        if "name" in gdf.columns
                        else None
                    ),

                    limpar_valor(
                        row["highway"]
                        if "highway" in gdf.columns
                        else None
                    ),

                    limpar_valor(
                        row["surface"]
                        if "surface" in gdf.columns
                        else None
                    ),

                    limpar_valor(
                        row["maxspeed"]
                        if "maxspeed" in gdf.columns
                        else None
                    ),

                    limpar_valor(
                        row["lanes"]
                        if "lanes" in gdf.columns
                        else None
                    ),

                    limpar_valor(
                        row["oneway"]
                        if "oneway" in gdf.columns
                        else None
                    ),

                    limpar_valor(
                        row["bridge"]
                        if "bridge" in gdf.columns
                        else None
                    ),

                    limpar_valor(
                        row["carriageway_ref"]
                        if "carriageway_ref" in gdf.columns
                        else None
                    ),

                    Jsonb(atributos),

                    geojson_geom
                )

                cur.execute(sql, valores)

                contador = indice + 1

                if contador % 500 == 0:
                    print(
                        f"  {contador:,} / "
                        f"{total:,} geometrias"
                    )

        conn.commit()

    # --------------------------------------------------------
    # VALIDAÇÃO
    # --------------------------------------------------------

    print("\nValidando dados gravados...")

    with conectar() as conn:

        with conn.cursor() as cur:

            cur.execute("""
                SELECT COUNT(*)
                FROM tcc.rodovias_osm_raw;
            """)

            quantidade = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*)
                FROM tcc.rodovias_osm_raw
                WHERE geom IS NOT NULL;
            """)

            geometrias = cur.fetchone()[0]

    print("\n" + "=" * 70)
    print("IMPORTAÇÃO CONCLUÍDA")
    print("=" * 70)

    print(f"GeoJSON     : {len(gdf):,}")
    print(f"Banco       : {quantidade:,}")
    print(f"Com geometria: {geometrias:,}")

    if quantidade == len(gdf):
        print(
            "\nOK - quantidade importada "
            "confere com o GeoJSON."
        )
    else:
        print(
            "\nATENÇÃO - quantidade divergente!"
        )


if __name__ == "__main__":
    main()