import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)


print("=" * 85)
print("PREENCHIMENTO DA METEOROLOGIA HORÁRIA DOS SEGMENTOS")
print("=" * 85)


# ============================================================
# VALIDA DESTINO
# ============================================================

with engine.connect() as conn:
    total_destino = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.meteorologia_segmentos_horaria;
        """)
    ).scalar()

print(f"\nRegistros existentes no destino: {total_destino:,}")
print("Modo incremental: os registros existentes serão preservados.")


# ============================================================
# CRIA TABELA TEMPORÁRIA COM HORAS NECESSÁRIAS
#
# Para cada incêndio:
# hora do incêndio arredondada
# menos 168 horas
# até a hora atual
# ============================================================

print("\nGerando segmento/hora necessários...")

sql_horas = """
DROP TABLE IF EXISTS tcc.tmp_horas_interesse;

CREATE UNLOGGED TABLE tcc.tmp_horas_interesse AS

SELECT DISTINCT
    i.segmento_id,
    DATE_TRUNC('hour', i.data_hora_inicio)
        - (gs.horas_antes * INTERVAL '1 hour') AS data_hora
    
FROM tcc.incendios_segmentados i

CROSS JOIN
(
    VALUES
        (169),
        (170),
        (171),
        (172)
) AS gs(horas_antes);
"""


with engine.begin() as conn:
    conn.execute(text(sql_horas))
    
print("\nRemovendo horas que já existem no cache...")

sql_remover_existentes = """
DELETE FROM tcc.tmp_horas_interesse h
USING tcc.meteorologia_segmentos_horaria m
WHERE m.segmento_id = h.segmento_id
  AND m.data_hora = h.data_hora;
"""

with engine.begin() as conn:
    conn.execute(text(sql_remover_existentes))


with engine.connect() as conn:
    total_horas = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.tmp_horas_interesse;
        """)
    ).scalar()

print(f"Combinações segmento/hora únicas: {total_horas:,}")


with engine.connect() as conn:
    total_horas = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.tmp_horas_interesse;
        """)
    ).scalar()


print(f"Combinações segmento/hora únicas: {total_horas:,}")


# ============================================================
# ÍNDICE TEMPORÁRIO
# ============================================================

print("\nCriando índice temporário...")

with engine.begin() as conn:
    conn.execute(
        text("""
            CREATE INDEX idx_tmp_horas_interesse
            ON tcc.tmp_horas_interesse (
                segmento_id,
                data_hora
            );
        """)
    )


# ============================================================
# RESOLVE METEOROLOGIA
#
# Para cada segmento/hora:
# pega estações <= 100 km
# e escolhe o primeiro valor válido por variável
# ============================================================

print("\nResolvendo meteorologia com fallback até 100 km...")
print("Essa etapa pode demorar alguns minutos.")


sql_insert = """
INSERT INTO tcc.meteorologia_segmentos_horaria
(
    segmento_id,
    data_hora,

    temperatura,
    umidade,
    precipitacao,
    vento,
    rajada,

    temperatura_estacao,
    umidade_estacao,
    precipitacao_estacao,
    vento_estacao,
    rajada_estacao,

    temperatura_distancia_km,
    umidade_distancia_km,
    precipitacao_distancia_km,
    vento_distancia_km,
    rajada_distancia_km,

    temperatura_ranking,
    umidade_ranking,
    precipitacao_ranking,
    vento_ranking,
    rajada_ranking
)

SELECT
    h.segmento_id,
    h.data_hora,

    -- TEMPERATURA
    temp.valor,
    umi.valor,
    prec.valor,
    vento.valor,
    raj.valor,

    temp.codigo_estacao,
    umi.codigo_estacao,
    prec.codigo_estacao,
    vento.codigo_estacao,
    raj.codigo_estacao,

    temp.distancia_km,
    umi.distancia_km,
    prec.distancia_km,
    vento.distancia_km,
    raj.distancia_km,

    temp.ranking,
    umi.ranking,
    prec.ranking,
    vento.ranking,
    raj.ranking

FROM tcc.tmp_horas_interesse h


-- ============================================================
-- TEMPERATURA
-- ============================================================

LEFT JOIN LATERAL (

    SELECT
        m.temperatura AS valor,
        se.codigo_estacao,
        se.distancia_km,
        se.ranking

    FROM tcc.segmentos_estacoes se

    JOIN tcc.meteorologia_raw m
        ON m.codigo_estacao = se.codigo_estacao
       AND m.data_hora = h.data_hora

    WHERE
        se.segmento_id = h.segmento_id
        AND se.distancia_km <= 100
        AND m.temperatura IS NOT NULL

    ORDER BY se.distancia_km

    LIMIT 1

) temp ON TRUE


-- ============================================================
-- UMIDADE
-- ============================================================

LEFT JOIN LATERAL (

    SELECT
        m.umidade AS valor,
        se.codigo_estacao,
        se.distancia_km,
        se.ranking

    FROM tcc.segmentos_estacoes se

    JOIN tcc.meteorologia_raw m
        ON m.codigo_estacao = se.codigo_estacao
       AND m.data_hora = h.data_hora

    WHERE
        se.segmento_id = h.segmento_id
        AND se.distancia_km <= 100
        AND m.umidade IS NOT NULL

    ORDER BY se.distancia_km

    LIMIT 1

) umi ON TRUE


-- ============================================================
-- PRECIPITAÇÃO
-- ============================================================

LEFT JOIN LATERAL (

    SELECT
        m.precipitacao AS valor,
        se.codigo_estacao,
        se.distancia_km,
        se.ranking

    FROM tcc.segmentos_estacoes se

    JOIN tcc.meteorologia_raw m
        ON m.codigo_estacao = se.codigo_estacao
       AND m.data_hora = h.data_hora

    WHERE
        se.segmento_id = h.segmento_id
        AND se.distancia_km <= 100
        AND m.precipitacao IS NOT NULL

    ORDER BY se.distancia_km

    LIMIT 1

) prec ON TRUE


-- ============================================================
-- VENTO
-- ============================================================

LEFT JOIN LATERAL (

    SELECT
        m.vento_velocidade AS valor,
        se.codigo_estacao,
        se.distancia_km,
        se.ranking

    FROM tcc.segmentos_estacoes se

    JOIN tcc.meteorologia_raw m
        ON m.codigo_estacao = se.codigo_estacao
       AND m.data_hora = h.data_hora

    WHERE
        se.segmento_id = h.segmento_id
        AND se.distancia_km <= 100
        AND m.vento_velocidade IS NOT NULL

    ORDER BY se.distancia_km

    LIMIT 1

) vento ON TRUE


-- ============================================================
-- RAJADA
-- ============================================================

LEFT JOIN LATERAL (

    SELECT
        m.vento_rajada AS valor,
        se.codigo_estacao,
        se.distancia_km,
        se.ranking

    FROM tcc.segmentos_estacoes se

    JOIN tcc.meteorologia_raw m
        ON m.codigo_estacao = se.codigo_estacao
       AND m.data_hora = h.data_hora

    WHERE
        se.segmento_id = h.segmento_id
        AND se.distancia_km <= 100
        AND m.vento_rajada IS NOT NULL

    ORDER BY se.distancia_km

    LIMIT 1

) raj ON TRUE
ON CONFLICT (segmento_id, data_hora)
DO NOTHING;
"""


with engine.begin() as conn:
    conn.execute(text(sql_insert))


# ============================================================
# VALIDAÇÃO
# ============================================================

with engine.connect() as conn:

    total_final = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.meteorologia_segmentos_horaria;
        """)
    ).scalar()


print(f"\nRegistros inseridos: {total_final:,}")


# ============================================================
# COBERTURA
# ============================================================

with engine.connect() as conn:

    cobertura = conn.execute(
        text("""
            SELECT
                COUNT(*) AS total,

                COUNT(temperatura) AS temperatura,
                COUNT(umidade) AS umidade,
                COUNT(precipitacao) AS precipitacao,
                COUNT(vento) AS vento,
                COUNT(rajada) AS rajada

            FROM tcc.meteorologia_segmentos_horaria;
        """)
    ).mappings().one()


total = cobertura["total"]

print("\nCobertura:")

for campo in [
    "temperatura",
    "umidade",
    "precipitacao",
    "vento",
    "rajada",
]:

    qtd = cobertura[campo]

    pct = qtd / total * 100 if total else 0

    print(
        f"{campo:15s}: "
        f"{qtd:>10,} / {total:,} "
        f"({pct:6.2f}%)"
    )


# ============================================================
# REMOVE TEMPORÁRIA
# ============================================================

print("\nRemovendo tabela temporária...")

with engine.begin() as conn:
    conn.execute(
        text("""
            DROP TABLE IF EXISTS tcc.tmp_horas_interesse;
        """)
    )


print("\n" + "=" * 85)
print("PROCESSO CONCLUÍDO")
print("=" * 85)