import os
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)


print("=" * 75)
print("ANÁLISE DA GEOMETRIA DA SP-348")
print("=" * 75)


# ============================================================
# 1. RESUMO DAS GEOMETRIAS
# ============================================================

sql_resumo = """
SELECT
    COUNT(*) AS geometrias,
    SUM(ST_Length(geom_metrica)) / 1000.0 AS comprimento_somado_km,
    MIN(ST_Length(geom_metrica)) / 1000.0 AS menor_trecho_km,
    MAX(ST_Length(geom_metrica)) / 1000.0 AS maior_trecho_km
FROM tcc.rodovias_tratadas
WHERE rodovia = 'SP-348';
"""

resumo = pd.read_sql(sql_resumo, engine)

print("\nResumo das geometrias:")
print(resumo.to_string(index=False))


# ============================================================
# 2. TIPOS DAS GEOMETRIAS
# ============================================================

sql_tipos = """
SELECT
    ST_GeometryType(geom_metrica) AS tipo,
    COUNT(*) AS quantidade
FROM tcc.rodovias_tratadas
WHERE rodovia = 'SP-348'
GROUP BY ST_GeometryType(geom_metrica)
ORDER BY quantidade DESC;
"""

tipos = pd.read_sql(sql_tipos, engine)

print("\nTipos geométricos:")
print(tipos.to_string(index=False))


# ============================================================
# 3. EXTENSÃO GEOGRÁFICA DA SP-348
# ============================================================

sql_extent = """
SELECT
    ST_XMin(ext) AS xmin,
    ST_YMin(ext) AS ymin,
    ST_XMax(ext) AS xmax,
    ST_YMax(ext) AS ymax
FROM (
    SELECT ST_Extent(geom_4326) AS ext
    FROM tcc.rodovias_tratadas
    WHERE rodovia = 'SP-348'
) q;
"""

extent = pd.read_sql(sql_extent, engine)

print("\nEnvelope geográfico:")
print(extent.to_string(index=False))


# ============================================================
# 4. PONTOS REPRESENTATIVOS DOS PRIMEIROS SEGMENTOS
# ============================================================

sql_segmentos = """
SELECT
    s.segmento_id,
    s.km_inicio,
    s.km_fim,
    p.latitude,
    p.longitude,
    p.qtd_pontos
FROM tcc.segmentos_rodovias s
LEFT JOIN tcc.segmentos_posicao p
    ON p.segmento_id = s.segmento_id
WHERE s.rodovia = 'SP-348'
ORDER BY s.numero_segmento
LIMIT 8;
"""

segmentos = pd.read_sql(sql_segmentos, engine)

print("\nPrimeiros segmentos da SP-348:")
print(segmentos.to_string(index=False))


# ============================================================
# 5. DISTÂNCIAS ENTRE OS PRIMEIROS PONTOS CONHECIDOS
# ============================================================

sql_distancias = """
WITH pontos AS (
    SELECT
        s.numero_segmento,
        s.segmento_id,
        s.km_inicio,
        s.km_fim,
        p.geom
    FROM tcc.segmentos_rodovias s
    JOIN tcc.segmentos_posicao p
        ON p.segmento_id = s.segmento_id
    WHERE s.rodovia = 'SP-348'
)
SELECT
    a.segmento_id AS segmento_atual,
    b.segmento_id AS proximo_segmento,
    ROUND(
        ST_Distance(
            ST_Transform(a.geom, 31983),
            ST_Transform(b.geom, 31983)
        )::numeric / 1000,
        3
    ) AS distancia_km
FROM pontos a
JOIN pontos b
    ON b.numero_segmento = a.numero_segmento + 1
ORDER BY a.numero_segmento
LIMIT 10;
"""

distancias = pd.read_sql(sql_distancias, engine)

print("\nDistância entre posições representativas consecutivas:")
print(distancias.to_string(index=False))


print("\n" + "=" * 75)
print("ANÁLISE CONCLUÍDA")
print("=" * 75)