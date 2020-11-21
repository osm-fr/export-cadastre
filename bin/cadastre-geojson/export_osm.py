#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with it. If not, see <http://www.gnu.org/licenses/>.

"""

Exporte les fichiers osm depuis la base de donnée.

"""

import os
import re
import sys
import json
import time
import os.path
import argparse
import psycopg2

try:
    from osm.pyosm import *
except:
    sys.stderr.write("PLEASE INSTALL https://github.com/werner2101/python-osm");
    sys.exit(-1)

from . import db
from .import_json import normalise_numero_departement
from .import_json import normalise_numero_commune

SOURCE_TAG = "cadastre-dgi-fr source : Direction Générale des Finances Publiques - Cadastre. Mise à jour : " + time.strftime("%Y")


def normalise_numero_insee(numero_departement, numero_commune):
    numero_departement = normalise_numero_departement(numero_departement)
    numero_commune = normalise_numero_commune(numero_commune)
    if numero_departement.startswith("0"):
        return numero_departement[1:] + numero_commune
    else:
        assert numero_commune[0] == "0"
        return numero_departement + numero_commune[1:]


def number_generator(start, incr):
    value=start
    while True:
        yield value
        value = value + incr
ids_osm = number_generator(-1, -1)


def lonlat_to_osm_node(xxx_todo_changeme, osmfile):
    (lon,lat) = xxx_todo_changeme
    lon=float("%.7f" % lon)
    lat=float("%.7f" % lat)
    if not hasattr(osmfile, "nodes_by_lonlat"):
        osmfile.nodes_by_lonlat = {}
    node = osmfile.nodes_by_lonlat.get((lon,lat))
    if node is None:
        node = Node({"lon":lon, "lat":lat, "id":next(ids_osm)}, {})
        osmfile.nodes_by_lonlat[(lon,lat)] = node
        osmfile.nodes[node.id] = node
    return node


def parse_lonlat_str(lonlat_str):
    return list(map(float, lonlat_str.split(" ")))


def lonlat_list_str_to_osm_way(lonlat_list_str, osmfile):
    lonlats = [parse_lonlat_str(p) for p in lonlat_list_str.split(",")]
    nodes = [lonlat_to_osm_node(ll, osmfile) for ll in lonlats]
    way = Way({"id": next(ids_osm)}, {}, [n.id for n in nodes], osmfile)
    osmfile.ways[way.id] = way
    return way


def latlon_polygons_str_to_osm(polygons_str, osmfile):
    outers, inners = [], []
    for polygon in polygons_str:
        linear_rings = [lonlat_list_str_to_osm_way(lll, osmfile) for lll in  polygon.split("),(")]
        outers.append(linear_rings[0])
        inners.extend(linear_rings[1:])
    if len(outers) == 1 and len(inners) == 0:
        return outers[0]
    else:
        for way in outers + inners: way.tags["source"] = SOURCE_TAG
        members = [("w", way.id, "outer") for way in outers] + \
                  [("w", way.id, "inner") for way in inners]
        relation = Relation({"id": next(ids_osm)}, {"type": "multipolygon"}, members, osmfile)
        osmfile.relations[relation.id] = relation
        return relation


def st_geometry_to_osm_primitive(st_geometry, osmfile):
    if st_geometry.startswith("POINT("):
        assert st_geometry.endswith(")")
        return lonlat_to_osm_node(parse_lonlat_str(st_geometry[6:-1]), osmfile)
    elif st_geometry.startswith("LINESTRING("):
        assert st_geometry.endswith(")")
        return lonlat_list_str_to_osm_way(st_geometry[11:-1], osmfile)
    elif st_geometry.startswith("POLYGON(("):
        assert st_geometry.endswith("))")
        return latlon_polygons_str_to_osm([st_geometry[9:-2]], osmfile)
    elif st_geometry.startswith("MULTIPOLYGON((("):
        assert st_geometry.endswith(")))")
        return latlon_polygons_str_to_osm(st_geometry[15:-3].split(")),(("), osmfile)
    else:
        print(st_geometry)
        raise Exception("geomtry kind not supported yet:" + st_geometry.split("(")[0])


def commune_geometry_sql_expression(numero_departement, numero_commune):
    numero_departement  = normalise_numero_departement(numero_departement)
    numero_commune = normalise_numero_commune(numero_commune)
    return "(SELECT geometry FROM " + db.TABLE_PREFIX + "commune WHERE departement='%s' AND idu=%d)" % \
        (numero_departement, int(numero_commune))

def liste_numero_communes(numero_departement):
    numero_departement = normalise_numero_departement(numero_departement)
    db.execute("SELECT idu FROM " + db.TABLE_PREFIX + "commune WHERE departement=%s", [numero_departement])
    return [normalise_numero_commune(result[0]) for result in db.cur]

def liste_parcelles_commune(numero_departement, numero_commune, attributs):
    if not "idu" in attributs: attributs.append("idu")
    db.execute("SELECT " + ", ".join(attributs) + " FROM " + db.TABLE_PREFIX + "parcelle WHERE ST_Intersects(geometry, {})".format(
        commune_geometry_sql_expression(numero_departement, numero_commune)))
    return [result for result in db.cur if result.idu.startswith(numero_commune)]


def sql_select_dans_commune(table, params, condition, numero_departement, numero_commune):
    table = db.TABLE_PREFIX + table
    params = ", ".join([""] + params)
    condition = (condition + " AND ") if condition else ""
    db.execute("""SELECT ST_AsText(geometry) AS geometry, update_date, object_rid, tex{0}
               FROM {1}
               WHERE  {2} ST_Intersects(geometry, {3})""".format(
                        params, table, condition,
                        commune_geometry_sql_expression(numero_departement, numero_commune)))
    return db.cur


def sql_result_to_osm(result, numero_departement, osmfile):
    numero_departement = normalise_numero_departement(numero_departement)
    item = st_geometry_to_osm_primitive(result.geometry, osmfile)
    item.tags["source:date"] = str(result.update_date)
    item.tags["source"] = SOURCE_TAG
    item.tags["ref:FR:cadastre"] = numero_departement + ":" + str(result.object_rid)
    if result.tex:
        item.tags["name"] = " ".join(result.tex).decode("utf-8").strip()
    return item


def export_batiments(numero_departement, numero_commune, osmfile):
    # Les églises contienent une croix: sym=14 dans la table tline,
    eglise = "EXISTS (SELECT * FROM """ + db.TABLE_PREFIX + "tline as tline WHERE tline.sym=14 AND ST_Contains(" + db.TABLE_PREFIX + "batiment.geometry, tline.geometry)) AS eglise"
    for result in sql_select_dans_commune("batiment", ["creat_date", "dur", eglise], "ST_Area(geometry) > 0", numero_departement, numero_commune):
        item = sql_result_to_osm(result, numero_departement, osmfile)
        if result.eglise:
            item.tags["building"] = "church"
            item.tags["religion"] = "christian"
        else:
            item.tags["building"] = "yes"
        item.tags["start_date"] = str(result.creat_date)
        if result.dur == 2:
            item.tags["wall"] = "no"


def export_cimetieres(numero_departement, numero_commune, osmfile):
    for result in sql_select_dans_commune("tsurf", [], "sym = 51 AND ST_Area(geometry) > 0", numero_departement, numero_commune):
        item = sql_result_to_osm(result, numero_departement, osmfile)
        item.tags["landuse"] = "cemetery"


def export_eau(numero_departement, numero_commune, osmfile):
    for result in sql_select_dans_commune("tsurf", ["sym", "ST_Area(geometry::geography) AS area"], "ST_Area(geometry) > 0", numero_departement, numero_commune):
        if result.sym in [34, 65]:
            item = sql_result_to_osm(result, numero_departement, osmfile)
            item.tags["area"] = str(result.area)
            if result.sym == 34 or result.area > 150:
                item.tags["natural"] = "water"
            else:
                item.tags["leisure"] = "swimming_pool"
                item.tags["access"] = "private"
    for result in sql_select_dans_commune("tronfluv", [], "", numero_departement, numero_commune):
        item = sql_result_to_osm(result, numero_departement, osmfile)
        item.tags["waterway"] = "riverbank"


def export_lieudit(numero_departement, numero_commune, osmfile):
    for result in sql_select_dans_commune("lieudit", [], "", numero_departement, numero_commune):
        item = sql_result_to_osm(result, numero_departement, osmfile)
        item.tags["place"] = ""


def export_petits_noms(numero_departement, numero_commune, osmfile):
    numero_regex = re.compile("^[0-9]*$")
    for result in sql_select_dans_commune("voiep", [], "", numero_departement, numero_commune):
        if not numero_regex.match(result.text):
            item = sql_result_to_osm(result, numero_departement, osmfile)


def export_voies(numero_departement, numero_commune, osmfile):
    for result in sql_select_dans_commune("zoncommuni", [], "", numero_departement, numero_commune):
        item = sql_result_to_osm(result, numero_departement, osmfile)
        item.tags["highway"] = ""
    for result in sql_select_dans_commune("tronroute", [], "", numero_departement, numero_commune):
        item = sql_result_to_osm(result, numero_departement, osmfile)


class OSMFile(OSMXMLFile):
    def is_empty(self):
        len(self.nodes) + len(self.ways) + len(self.relations) == 0
    def write_if_not_empty(self, filename):
        if not self.is_empty(): self.write(filename)

def export_osm(departement, commune):
    departement = normalise_numero_departement(departement)
    commune = normalise_numero_commune(commune)
    numero_insee = normalise_numero_insee(departement, commune)
    prefix = numero_insee  + "-"

    osmfile = OSMFile()
    export_batiments(departement, commune, osmfile)
    osmfile.write_if_not_empty(prefix + "batiment.osm")

    osmfile = OSMFile()
    export_eau(departement, commune, osmfile)
    osmfile.write_if_not_empty(prefix + "eau.osm")

    osmfile = OSMFile()
    export_cimetieres(departement, commune, osmfile)
    osmfile.write_if_not_empty(prefix + "cimetiere.osm")

    osmfile = OSMFile(options={"upload":"false"})
    export_lieudit(departement, commune, osmfile)
    osmfile.write_if_not_empty(prefix + "lieudit.osm")

    osmfile = OSMFile(options={"upload":"false"})
    export_voies(departement, commune, osmfile)
    osmfile.write_if_not_empty(prefix + "voies-NE_PAS_ENVOYER_SUR_OSM.osm")

    osmfile = OSMFile(options={"upload":"false"})
    export_petits_noms(departement, commune, osmfile)
    osmfile.write_if_not_empty(prefix + "petis-noms-NE_PAS_ENVOYER_SUR_OSM.osm")

def main(args):
    parser = argparse.ArgumentParser(description="Export d'une commune au format .osm")
    parser.add_argument("departement", help="code departement", type=str)
    parser.add_argument("commune", help="code commune", type=str)
    args = parser.parse_args(args)
    if (args.commune.lower() in ["all", "toutes"]):
        for commune in liste_numero_communes(args.departement):
            export_osm(args.departement, commune)
    else:
        export_osm(args.departement, args.commune)

if __name__ == '__main__':
    main(sys.argv[1:])

