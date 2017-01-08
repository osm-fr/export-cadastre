CREATE TYPE segmented_choice_kind AS ENUM ( 'join',  'keep', 'unknown');
CREATE TYPE segmented_resolution_kind AS ENUM ('none', 'join', 'keep', 'unknown', 'outofdate', 'undecided');

CREATE TABLE segmented_cases (
    id SERIAL PRIMARY KEY,
    way1_osm_id bigint,
    way2_osm_id bigint,
    way1_geom geometry,
    way2_geom geometry,
    center geometry,
    creation_time timestamp without time zone,
    resolution_time timestamp without time zone,
    resolution segmented_resolution_kind default 'none',
    CONSTRAINT enforce_osm_id_order CHECK (way2_osm_id > way1_osm_id),
    CONSTRAINT enforce_srid1 CHECK (st_srid(way1_geom ) = 4326),
    CONSTRAINT enforce_srid2 CHECK (st_srid(way2_geom ) = 4326),
    CONSTRAINT enforce_srid3 CHECK (st_srid(center) = 4326)
);


CREATE TABLE segmented_contributions (
    case_id SERIAL,
    ip inet,
    "time" timestamp without time zone,
    choice segmented_choice_kind,
    session integer
);

CREATE VIEW segmented_contributions_rank AS
 SELECT case_id,
    choice,
    nb,
    first,
    last,
    rank() OVER (PARTITION BY case_id ORDER BY nb DESC) AS rank
   FROM ( SELECT case_id,
            choice,
            count(*) AS nb,
            min("time") AS first,
            max("time") AS last
           FROM segmented_contributions
          GROUP BY case_id, choice) c;


CREATE VIEW segmented_contributions_next AS
 SELECT c1.case_id,
    ((c1.nb)::numeric - COALESCE(sum(c2.nb), (0)::numeric)) AS nb,
    c1.last,
    ((c1.nb)::numeric + COALESCE(sum(c2.nb), (0)::numeric)) AS total
   FROM (segmented_contributions_rank c1
     LEFT JOIN segmented_contributions_rank c2 ON (((c2.case_id = c1.case_id) AND (c2.rank > 1))))
  WHERE ((c1.rank = 1))-- AND (c1.nb >= 3))
  GROUP BY c1.case_id, c1.choice, c1.nb, c1.rank, c1.first, c1.last
 HAVING (((c1.nb)::numeric - COALESCE(sum(c2.nb), (0)::numeric)) < (3)::numeric);



CREATE INDEX segmented_cases_id      ON segmented_cases USING btree (id);
CREATE INDEX segmented_cases_osm_id1 ON segmented_cases USING btree (way1_osm_id);
CREATE INDEX segmented_cases_osm_id2 ON segmented_cases USING btree (way2_osm_id);
CREATE INDEX segmented_cases_osm_ids ON segmented_cases USING btree (way1_osm_id, way2_osm_id);
CREATE INDEX segmented_cases_geom    ON segmented_cases USING gist(center) WHERE (resolution = 'none');

CREATE INDEX segmented_contributions_case_id    ON segmented_contributions USING btree (case_id);
CREATE INDEX segmented_contributions_case_id_ip ON segmented_contributions USING btree (case_id,ip);
CREATE INDEX segmented_contributions_ip         ON segmented_contributions USING btree (ip);

