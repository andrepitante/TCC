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


print("=" * 90)
print("CRIAÇÃO DAS AMOSTRAS NEGATIVAS - HORIZONTE DE 4 HORAS")
print("=" * 90)


# ============================================================
# VALIDAÇÕES
# ============================================================

with engine.connect() as conn:

    total_positivos = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.amostras_positivas_4h;
        """)
    ).scalar()

    total_negativos_existentes = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.amostras_negativas_4h;
        """)
    ).scalar()


print(f"\nAmostras positivas            : {total_positivos:,}")
print(f"Negativos já existentes       : {total_negativos_existentes:,}")
print(f"Negativos desejados (2x)      : {total_positivos * 2:,}")


if total_negativos_existentes > 0:
    raise RuntimeError(
        "A tabela tcc.amostras_negativas_4h já possui registros."
    )


# ============================================================
# ÍNDICE PARA ACELERAR A PROCURA DE INCÊNDIOS
# ============================================================

print("\nVerificando índice dos incêndios...")

with engine.begin() as conn:
    conn.execute(
        text("""
            CREATE INDEX IF NOT EXISTS
                idx_incendios_segmentados_segmento_datahora
            ON tcc.incendios_segmentados (
                segmento_id,
                data_hora_inicio
            );
        """)
    )


# ============================================================
# GRUPOS POSITIVOS
# ============================================================

print("\nCriando grupos segmento + mês + hora...")

sql_grupos = """
DROP TABLE IF EXISTS tcc.tmp_grupos_negativos;

CREATE UNLOGGED TABLE tcc.tmp_grupos_negativos AS

SELECT
    segmento_id,

    EXTRACT(
        MONTH FROM hora_referencia
    )::INTEGER AS mes,

    EXTRACT(
        HOUR FROM hora_referencia
    )::INTEGER AS hora,

    COUNT(*)::INTEGER AS positivos,

    (COUNT(*) * 2)::INTEGER AS negativos_desejados

FROM tcc.amostras_positivas_4h

GROUP BY
    segmento_id,
    EXTRACT(MONTH FROM hora_referencia),
    EXTRACT(HOUR FROM hora_referencia);
"""

with engine.begin() as conn:
    conn.execute(text(sql_grupos))


with engine.connect() as conn:
    total_grupos = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.tmp_grupos_negativos;
        """)
    ).scalar()


print(f"Grupos encontrados            : {total_grupos:,}")


# ============================================================
# GERA CANDIDATOS
# ============================================================

print("\nGerando candidatos negativos...")
print("Esta é a etapa mais pesada e pode levar alguns minutos.")


sql_candidatos = """
DROP TABLE IF EXISTS tcc.tmp_candidatos_negativos;

CREATE UNLOGGED TABLE tcc.tmp_candidatos_negativos AS

SELECT

    g.segmento_id,

    (
        d.dia
        + make_interval(hours => g.hora)
    ) AS hora_referencia,

    g.negativos_desejados

FROM tcc.tmp_grupos_negativos g

CROSS JOIN LATERAL
(
    SELECT gs::timestamp AS dia

    FROM generate_series(
        TIMESTAMP '2015-01-01 00:00:00',
        TIMESTAMP '2026-06-30 00:00:00',
        INTERVAL '1 day'
    ) gs

    WHERE
        EXTRACT(MONTH FROM gs)::INTEGER = g.mes

) d

WHERE

    (
        d.dia
        + make_interval(hours => g.hora)
    ) <= TIMESTAMP '2026-06-30 21:00:00';
"""

with engine.begin() as conn:
    conn.execute(text(sql_candidatos))


print("Criando índice temporário...")

with engine.begin() as conn:
    conn.execute(
        text("""
            CREATE INDEX idx_tmp_candidatos_negativos
            ON tcc.tmp_candidatos_negativos (
                segmento_id,
                hora_referencia
            );
        """)
    )


with engine.connect() as conn:
    total_candidatos = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.tmp_candidatos_negativos;
        """)
    ).scalar()


print(f"Candidatos gerados            : {total_candidatos:,}")


# ============================================================
# REMOVE HORÁRIOS POSITIVOS
# ============================================================

print("\nRemovendo horas positivas...")

with engine.begin() as conn:
    conn.execute(
        text("""
            DELETE FROM tcc.tmp_candidatos_negativos c
            USING tcc.amostras_positivas_4h p

            WHERE
                p.segmento_id = c.segmento_id
                AND p.hora_referencia = c.hora_referencia;
        """)
    )


# ============================================================
# REMOVE HORÁRIOS COM INCÊNDIO NAS PRÓXIMAS 4H
# ============================================================

print("Removendo candidatos com incêndio nas próximas 4 horas...")

with engine.begin() as conn:
    conn.execute(
        text("""
            DELETE FROM tcc.tmp_candidatos_negativos c

            WHERE EXISTS
            (
                SELECT 1

                FROM tcc.incendios_segmentados i

                WHERE
                    i.segmento_id = c.segmento_id

                    AND i.data_hora_inicio >
                        c.hora_referencia

                    AND i.data_hora_inicio <=
                        c.hora_referencia
                        + INTERVAL '4 hours'
            );
        """)
    )


with engine.connect() as conn:
    total_validos = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM tcc.tmp_candidatos_negativos;
        """)
    ).scalar()


print(f"Candidatos válidos            : {total_validos:,}")


# ============================================================
# SELECIONA 2 NEGATIVOS POR POSITIVO
#
# md5 é utilizado para fornecer uma ordenação pseudoaleatória,
# mas reproduzível.
# ============================================================

print("\nSelecionando negativos finais...")


sql_insert = """
WITH classificados AS
(
    SELECT

        c.segmento_id,
        c.hora_referencia,
        c.negativos_desejados,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                c.segmento_id,
                EXTRACT(MONTH FROM c.hora_referencia),
                EXTRACT(HOUR FROM c.hora_referencia)

            ORDER BY
                md5(
                    c.segmento_id
                    || '|'
                    || c.hora_referencia::text
                )
        ) AS rn

    FROM tcc.tmp_candidatos_negativos c
)

INSERT INTO tcc.amostras_negativas_4h
(
    segmento_id,
    rodovia,
    hora_referencia,
    incendio_proximas_4h
)

SELECT
    c.segmento_id,
    s.rodovia,
    c.hora_referencia,
    0

FROM classificados c

JOIN tcc.segmentos_rodovias s
    ON s.segmento_id = c.segmento_id

WHERE
    c.rn <= c.negativos_desejados

ON CONFLICT (
    segmento_id,
    hora_referencia
)
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
            FROM tcc.amostras_negativas_4h;
        """)
    ).scalar()

    duplicados = conn.execute(
        text("""
            SELECT
                COUNT(*) -
                COUNT(
                    DISTINCT (
                        segmento_id,
                        hora_referencia
                    )
                )
            FROM tcc.amostras_negativas_4h;
        """)
    ).scalar()

    conflitos = conn.execute(
        text("""
            SELECT COUNT(*)

            FROM tcc.amostras_negativas_4h n

            WHERE EXISTS
            (
                SELECT 1

                FROM tcc.incendios_segmentados i

                WHERE
                    i.segmento_id = n.segmento_id

                    AND i.data_hora_inicio >
                        n.hora_referencia

                    AND i.data_hora_inicio <=
                        n.hora_referencia
                        + INTERVAL '4 hours'
            );
        """)
    ).scalar()


print("\n" + "=" * 90)
print("RESULTADO")
print("=" * 90)

print(f"\nNegativos criados             : {total_final:,}")
print(f"Esperado                      : {total_positivos * 2:,}")
print(f"Duplicados                    : {duplicados:,}")
print(f"Conflitos com incêndio em 4h  : {conflitos:,}")


# ============================================================
# LIMPEZA
# ============================================================

print("\nRemovendo tabelas temporárias...")


with engine.begin() as conn:
    conn.execute(
        text("""
            DROP TABLE IF EXISTS tcc.tmp_candidatos_negativos;
            DROP TABLE IF EXISTS tcc.tmp_grupos_negativos;
        """)
    )


print("\n" + "=" * 90)
print("PROCESSO CONCLUÍDO")
print("=" * 90)