import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# ARGUMENTOS
#
# Exemplos:
#
# python completar_meteorologia_negativos.py 2015 1
# python completar_meteorologia_negativos.py 2015
# ============================================================

if len(sys.argv) < 2:
    raise SystemExit(
        "Uso: python completar_meteorologia_negativos.py ANO [MES]"
    )

ano = int(sys.argv[1])
mes = int(sys.argv[2]) if len(sys.argv) >= 3 else None

if mes is not None and not 1 <= mes <= 12:
    raise SystemExit("Mês inválido. Use valores entre 1 e 12.")


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)


print("=" * 90)
print("COMPLEMENTO DA METEOROLOGIA PARA AMOSTRAS NEGATIVAS")
print("=" * 90)

if mes is None:
    print(f"\nPeríodo selecionado: ano {ano}")
else:
    print(f"\nPeríodo selecionado: {mes:02d}/{ano}")


# ============================================================
# FILTRO DAS AMOSTRAS
# ============================================================

filtro_periodo = """
EXTRACT(YEAR FROM n.hora_referencia)::INTEGER = :ano
"""

parametros = {"ano": ano}

if mes is not None:
    filtro_periodo += """
    AND EXTRACT(MONTH FROM n.hora_referencia)::INTEGER = :mes
    """
    parametros["mes"] = mes


# ============================================================
# INFORMAÇÕES INICIAIS
# ============================================================

with engine.connect() as conn:

    total_cache_antes = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.meteorologia_segmentos_horaria;
        """)
    ).scalar()

    total_amostras = conn.execute(
        text(f"""
            SELECT COUNT(*)
            FROM tcc.amostras_negativas_4h n
            WHERE {filtro_periodo};
        """),
        parametros,
    ).scalar()


print(f"Amostras negativas no período : {total_amostras:,}")
print(f"Cache atual                    : {total_cache_antes:,}")


if total_amostras == 0:
    raise RuntimeError("Não existem amostras negativas nesse período.")


# ============================================================
# GERA AS HORAS NECESSÁRIAS
#
# Mantemos o mesmo padrão utilizado nas medições anteriores:
# hora_referencia - 168h até hora_referencia.
#
# Depois o cálculo das features utiliza:
# > hora_referencia - 168h
# <= hora_referencia
# ============================================================

print("\nGerando segmento/horas necessários...")


# Primeiro remove a temporária, caso tenha sobrado de execução anterior
with engine.begin() as conn:
    conn.execute(
        text("""
            DROP TABLE IF EXISTS tcc.tmp_horas_negativos;
        """)
    )

# Depois cria a tabela usando os parâmetros ano/mês
sql_horas = f"""
CREATE UNLOGGED TABLE tcc.tmp_horas_negativos AS

SELECT DISTINCT
    n.segmento_id,
    gs.data_hora

FROM tcc.amostras_negativas_4h n

CROSS JOIN LATERAL generate_series(
    n.hora_referencia - INTERVAL '168 hours',
    n.hora_referencia,
    INTERVAL '1 hour'
) AS gs(data_hora)

WHERE {filtro_periodo};
"""


with engine.begin() as conn:
    conn.execute(text(sql_horas), parametros)


with engine.connect() as conn:
    total_necessarias = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.tmp_horas_negativos;
        """)
    ).scalar()


print(f"Horas distintas necessárias   : {total_necessarias:,}")


# ============================================================
# ÍNDICE TEMPORÁRIO
# ============================================================

print("\nCriando índice temporário...")


with engine.begin() as conn:
    conn.execute(
        text("""
            CREATE INDEX idx_tmp_horas_negativos
            ON tcc.tmp_horas_negativos (
                segmento_id,
                data_hora
            );
        """)
    )


# ============================================================
# REMOVE O QUE JÁ EXISTE NO CACHE
# ============================================================

print("Removendo horas que já estão no cache...")


with engine.begin() as conn:
    conn.execute(
        text("""
            DELETE FROM tcc.tmp_horas_negativos h
            USING tcc.meteorologia_segmentos_horaria m

            WHERE
                m.segmento_id = h.segmento_id
                AND m.data_hora = h.data_hora;
        """)
    )


with engine.connect() as conn:
    total_faltantes = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.tmp_horas_negativos;
        """)
    ).scalar()


print(f"Horas realmente faltantes     : {total_faltantes:,}")


if total_faltantes == 0:

    print("\nNada para inserir.")

    with engine.begin() as conn:
        conn.execute(
            text("""
                DROP TABLE IF EXISTS tcc.tmp_horas_negativos;
            """)
        )

    raise SystemExit(0)


# ============================================================
# RESOLVE METEOROLOGIA
# ============================================================

print("\nResolvendo meteorologia com fallback até 100 km...")
print("Essa é a etapa mais pesada.")


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

FROM tcc.tmp_horas_negativos h


-- ============================================================
-- TEMPERATURA
-- ============================================================

LEFT JOIN LATERAL
(
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

LEFT JOIN LATERAL
(
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

LEFT JOIN LATERAL
(
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

LEFT JOIN LATERAL
(
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

LEFT JOIN LATERAL
(
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
# VALIDA RESULTADO
# ============================================================

with engine.connect() as conn:

    total_cache_depois = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.meteorologia_segmentos_horaria;
        """)
    ).scalar()


novos = total_cache_depois - total_cache_antes


print("\n" + "=" * 90)
print("RESULTADO")
print("=" * 90)

print(f"\nCache antes                   : {total_cache_antes:,}")
print(f"Registros novos inseridos     : {novos:,}")
print(f"Cache depois                  : {total_cache_depois:,}")

print(f"Horas faltantes esperadas     : {total_faltantes:,}")


# ============================================================
# LIMPEZA
# ============================================================

print("\nRemovendo tabela temporária...")


with engine.begin() as conn:
    conn.execute(
        text("""
            DROP TABLE IF EXISTS tcc.tmp_horas_negativos;
        """)
    )


print("\n" + "=" * 90)
print("PROCESSO CONCLUÍDO")
print("=" * 90)