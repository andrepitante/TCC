DROP TABLE IF EXISTS tcc.rodovias_tratadas;

CREATE TABLE tcc.rodovias_tratadas AS
SELECT
    id AS id_origem,

    CASE
        WHEN ref LIKE '%SP-021%' THEN 'SP-021'
        WHEN ref LIKE '%SP-280%' THEN 'SP-280'
        WHEN ref LIKE '%SP-300%' THEN 'SP-300'
        WHEN ref LIKE '%SP-330%' THEN 'SP-330'
        WHEN ref LIKE '%SP-348%' THEN 'SP-348'
    END AS rodovia,

    ref AS ref_original,
    nome,
    highway,
    surface,
    maxspeed,
    lanes,
    oneway,
    bridge,
    carriageway_ref,

    geom AS geom_4326,

    ST_Transform(
        geom,
        31983
    ) AS geom_metrica

FROM tcc.rodovias_osm_raw

WHERE
    (
           ref LIKE '%SP-021%'
        OR ref LIKE '%SP-280%'
        OR ref LIKE '%SP-300%'
        OR ref LIKE '%SP-330%'
        OR ref LIKE '%SP-348%'
    )

    AND (
        highway IS NULL
        OR highway NOT IN (
            'motorway_link',
            'trunk_link'
        )
    );
    