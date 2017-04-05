
CREATE TABLE cadastre_geojson_batiment (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry,
    dur smallint
);

CREATE TABLE cadastre_geojson_commune (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry,
    idu smallint
);

CREATE TABLE cadastre_geojson_tsurf (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry,
    sym smallint
);

CREATE TABLE cadastre_geojson_tline (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry,
    sym smallint
);

CREATE TABLE cadastre_geojson_tronfluv (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry
);

CREATE TABLE cadastre_geojson_lieudit (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry
);

CREATE TABLE cadastre_geojson_parcelle (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry,
    idu char(12),
    indp smallint,
    supf integer,
    coar char(1),
    adresses text[]
);

CREATE TABLE cadastre_geojson_numvoie (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry,
    parcelle_idu char(12),
    parcelle_contains boolean
);

CREATE TABLE cadastre_geojson_voiep (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry
);

CREATE TABLE cadastre_geojson_tronroute (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry,
    rcad text
);

CREATE TABLE cadastre_geojson_zoncommuni (
    departement char(3),
    object_rid integer,
    creat_date date,
    update_date date,
    tex text[],
    geometry geometry
);


CREATE INDEX cadastre_geojson_batiment_departement ON cadastre_geojson_batiment USING btree(departement);
CREATE INDEX cadastre_geojson_batiment_object_rid ON cadastre_geojson_batiment USING btree(object_rid);
CREATE INDEX cadastre_geojson_batiment_geometry ON cadastre_geojson_batiment USING gist(geometry);

CREATE INDEX cadastre_geojson_commune_departement ON cadastre_geojson_commune USING btree(departement);
CREATE INDEX cadastre_geojson_commune_object_rid ON cadastre_geojson_commune USING btree(object_rid);
CREATE INDEX cadastre_geojson_commune_geometry ON cadastre_geojson_commune USING gist(geometry);

CREATE INDEX cadastre_geojson_tsurf_departement ON cadastre_geojson_tsurf USING btree(departement);
CREATE INDEX cadastre_geojson_tsurf_object_rid ON cadastre_geojson_tsurf USING btree(object_rid);
CREATE INDEX cadastre_geojson_tsurf_geometry ON cadastre_geojson_tsurf USING gist(geometry);

CREATE INDEX cadastre_geojson_tline_departement ON cadastre_geojson_tline USING btree(departement);
CREATE INDEX cadastre_geojson_tline_object_rid ON cadastre_geojson_tline USING btree(object_rid);
CREATE INDEX cadastre_geojson_tline_geometry ON cadastre_geojson_tline USING gist(geometry);
CREATE INDEX cadastre_geojson_tline_sym ON cadastre_geojson_tline USING btree(sym);

CREATE INDEX cadastre_geojson_tronfluv_departement ON cadastre_geojson_tronfluv USING btree(departement);
CREATE INDEX cadastre_geojson_tronfluv_object_rid ON cadastre_geojson_tronfluv USING btree(object_rid);
CREATE INDEX cadastre_geojson_tronfluv_geometry ON cadastre_geojson_tronfluv USING gist(geometry);

CREATE INDEX cadastre_geojson_lieudit_departement ON cadastre_geojson_lieudit USING btree(departement);
CREATE INDEX cadastre_geojson_lieudit_object_rid ON cadastre_geojson_lieudit USING btree(object_rid);
CREATE INDEX cadastre_geojson_lieudit_geometry ON cadastre_geojson_lieudit USING gist(geometry);

CREATE INDEX cadastre_geojson_parcelle_departement ON cadastre_geojson_parcelle USING btree(departement);
CREATE INDEX cadastre_geojson_parcelle_object_rid ON cadastre_geojson_parcelle USING btree(object_rid);
CREATE INDEX cadastre_geojson_parcelle_geometry ON cadastre_geojson_parcelle USING gist(geometry);
CREATE INDEX cadastre_geojson_parcelle_idu ON cadastre_geojson_parcelle USING btree(idu);

CREATE INDEX cadastre_geojson_numvoie_departement ON cadastre_geojson_numvoie USING btree(departement);
CREATE INDEX cadastre_geojson_numvoie_object_rid ON cadastre_geojson_numvoie USING btree(object_rid);
CREATE INDEX cadastre_geojson_numvoie_geometry ON cadastre_geojson_numvoie USING gist(geometry);
CREATE INDEX cadastre_geojson_numvoie_parcelle_idu ON cadastre_geojson_numvoie USING btree(parcelle_idu);

CREATE INDEX cadastre_geojson_voiep_departement ON cadastre_geojson_voiep USING btree(departement);
CREATE INDEX cadastre_geojson_voiep_object_rid ON cadastre_geojson_voiep USING btree(object_rid);
CREATE INDEX cadastre_geojson_voiep_geometry ON cadastre_geojson_voiep USING gist(geometry);

CREATE INDEX cadastre_geojson_tronroute_departement ON cadastre_geojson_tronroute USING btree(departement);
CREATE INDEX cadastre_geojson_tronroute_object_rid ON cadastre_geojson_tronroute USING btree(object_rid);
CREATE INDEX cadastre_geojson_tronroute_geometry ON cadastre_geojson_tronroute USING gist(geometry);

CREATE INDEX cadastre_geojson_zoncommuni_departement ON cadastre_geojson_zoncommuni USING btree(departement);
CREATE INDEX cadastre_geojson_zoncommuni_object_rid ON cadastre_geojson_zoncommuni USING btree(object_rid);
CREATE INDEX cadastre_geojson_zoncommuni_geometry ON cadastre_geojson_zoncommuni USING gist(geometry);

