#!/usr/bin/env python
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

import db
from import_json import normalise_numero_departement
from import_json import normalise_numero_commune


SOURCE_TAG = u"cadastre-dgi-fr source : Direction Générale des Finances Publiques - Cadastre. Mise à jour : " + time.strftime("%Y")


def normalise_numero_insee(numero_departement, numero_commune):
    numero_departement = normalise_numero_departement(numero_departement)
    numero_commune = normalise_numero_commune(numero_commune)
    if numero_departement.startswith("0"):
        return numero_departement[1:] + numero_commune
    else:
        assert numero_commune[0] == "0"
        return numero_departement + numero_commune[1:]

def new_ids_generator():
    node_id=0
    while True:
        node_id = node_id - 1
        yield node_id
new_ids = new_ids_generator()


def lonlat_to_osm_node((lon,lat), osmfile):
    lon=float("%.7f" % lon)
    lat=float("%.7f" % lat)
    if not hasattr(osmfile, "nodes_by_lonlat"):
        osmfile.nodes_by_lonlat = {}
    node = osmfile.nodes_by_lonlat.get((lon,lat))
    if node is None:
        node = Node({"lon":lon, "lat":lat, "id":new_ids.next()}, {})
        osmfile.nodes_by_lonlat[(lon,lat)] = node
        osmfile.nodes[node.id] = node
    return node

def parse_lonlat_str(lonlat_str):
    return map(float, lonlat_str.split(" "))

def lonlat_list_str_to_osm_way(lonlat_list_str, osmfile):
    lonlats = [parse_lonlat_str(p) for p in lonlat_list_str.split(",")]
    nodes = [lonlat_to_osm_node(ll, osmfile) for ll in lonlats]
    way = Way({"id": new_ids.next()}, {}, [n.id for n in nodes], osmfile)
    osmfile.ways[way.id] = way
    return way

def latlon_polygons_str_to_osm(polygons_str, osmfile):
    outers = []
    inners = []
    for polygon in polygons_str:
        linear_rings = [lonlat_list_str_to_osm_way(lll, osmfile) for lll in  polygon.split("),(")]
        outers.append(linear_rings[0])
        inners.extend(linear_rings[1:])
    if len(outers) == 1 and len(inners) == 0:
        return linear_rings[0]
    else:
        members = []
        for way in outers:
            way.tags["source"] = SOURCE_TAG
            members.append(("w", way.id, "outer"))
        for way in inners:
            way.tags["source"] = SOURCE_TAG
            members.append(("w", way.id, "inner"))
        relation = Relation({"id": new_ids.next()}, {"type": "multipolygon"}, members, osmfile)
        osmfile.relations[relation.id] = relation
        return relation


def st_geometry_to_osm_primitive(st_geometry, osmfile):
    if st_geometry.startswith("POINT("):
        assert st_geometry.endswith(")")
        return lonlat_to_osm_node(parse_lonlat_str(st_geometry[6:-1]), osmfile)
    elif st_geometry.startswith("POLYGON(("):
        assert st_geometry.endswith("))")
        return latlon_polygons_str_to_osm([st_geometry[9:-2]], osmfile)
    elif st_geometry.startswith("MULTIPOLYGON((("):
        assert st_geometry.endswith(")))")
        return latlon_polygons_str_to_osm(st_geometry[15:-3].split(")),(("), osmfile)
    else:
        print st_geometry
        raise Exception("geomtry kind not supported yet:" + st_geometry.split("(")[0])


def commune_geometry_sql_expression(numero_departement, numero_commune):
    numero_departement  = normalise_numero_departement(numero_departement)
    numero_commune = normalise_numero_commune(numero_commune)
    return "(SELECT geometry FROM " + db.TABLE_PREFIX + "commune WHERE departement='%s' AND idu=%d)" % \
        (numero_departement, int(numero_commune))

def sql_select_dans_commune(table, params, condition, numero_departement, numero_commune):
    table = db.TABLE_PREFIX + table
    params = ", ".join([""] + params)
    condition = (condition + " AND ") if condition else ""
    db.execute("""SELECT ST_AsText(geometry), update_date, object_rid, tex{0}
               FROM {1}
               WHERE  {2} ST_Intersects(geometry, {3})""".format(
                        params, table, condition,
                        commune_geometry_sql_expression(numero_departement, numero_commune)))
    return db.cur

def sql_result_to_osm(result, numero_departement, osmfile):
    numero_departement = normalise_numero_departement(numero_departement)
    item = st_geometry_to_osm_primitive(result[0], osmfile)
    item.tags["source:date"] = str(result[1])
    item.tags["source"] = SOURCE_TAG
    item.tags["ref:FR:cadastre"] = numero_departement + ":" + str(result[2])
    if result[3]:
        item.tags["name"] = " ".join(result[3]).decode("utf-8").strip()
    return item

def export_batiment(numero_departement, numero_commune, osmfile):
    for result in sql_select_dans_commune("batiment", ["creat_date", "dur"], "ST_Area(geometry) > 0", numero_departement, numero_commune):
        item = sql_result_to_osm(result, numero_departement, osmfile)
        item.tags["building"] = "yes"
        item.tags["start_date"] = str(result[4])
        if result[5] == 2:
            item.tags["wall"] = "no"

def export_cemeteries(numero_departement, numero_commune, osmfile):
    for result in sql_select_dans_commune("tsurf", [], "sym = 51 AND ST_Area(geometry) > 0", numero_departement, numero_commune):
        item = sql_result_to_osm(result, numero_departement, osmfile)
        item.tags["landuse"] = "cemetery"

def export_water(numero_departement, numero_commune, osmfile):
    # FIXME: il faut transformer le SRID pour que ST_Area() retourne un résultat en m2.
    for result in sql_select_dans_commune("tsurf", ["sym", "ST_Area(geometry)"], "ST_Area(geometry) > 0", numero_departement, numero_commune):
        sym = result[4]
        area = result[5]
        if sym in [34, 65]:
            item = sql_result_to_osm(result, numero_departement, osmfile)
            if sym == 34 or area > 100:
                item.tags["natural"] = "water"
            elif sym == 65:
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
    for result in sql_select_dans_commune("voiep", [], "", numero_departement, numero_commune):
        text = " ".join(result[3]).decode("utf-8").strip()
        if not re.match("^[0-9]*$", text):
            item = sql_result_to_osm(result, numero_departement, osmfile)


def export_addr(numero_departement, numero_commune, osmfile):

    #SELECT tex FROM numvoie WHERE departement=%s LEFT JOIN parcelle
    #for result in sql_select_dans_commune("numvoie", [], "", numero_departement, numero_commune):
    #    item = sql_result_to_osm(result, numero_departement, osmfile)
    #    item.tags["addr:housenumber"] = item.tags["name"]
    #    del(item.tags["name"])

    db.execute("""SELECT
            tex,
            creat_date,
            update_date,
            object_rid,
            parcelle_idu,
            adresses,
            ST_AsText(numvoie_geometry) as original,
            ST_AsText(nearest) as nearest,
            ST_Distance_Sphere(numvoie_geometry, nearest) as distance,
            intersects
        FROM (
            SELECT
                numvoie.tex as  tex,
                numvoie.creat_date as creat_date,
                numvoie.update_date as update_date,
                numvoie.object_rid as object_rid,
                numvoie.parcelle_idu as parcelle_idu,
                parcelle.adresses as  adresses,
                numvoie.geometry as numvoie_geometry,
                ST_Transform(
                    ST_ClosestPoint(
                        ST_Transform(ST_ExteriorRing(ST_GeometryN(parcelle.geometry, 1)), 3857),
                        ST_Transform(numvoie.geometry, 3857)),
                    4326) as nearest,
                St_Intersects(numvoie.geometry, parcelle.geometry) as intersects
            FROM {0}numvoie as numvoie
            LEFT JOIN {0}parcelle as parcelle
            ON numvoie.parcelle_idu = parcelle.idu
            WHERE numvoie.departement=%s
                AND parcelle.departement=%s
                AND ST_Intersects(numvoie.geometry, {1})
        ) as req;""".format(
            db.TABLE_PREFIX,
            commune_geometry_sql_expression(numero_departement, numero_commune)),
        [numero_departement, numero_departement])
    for tex, creat_date, update_date, object_rid, parcelle_idu, adresses, original, nearest, distance, intersects in db.cur:
        geometry = nearest if (((distance < 4) and (not intersects)) or (intersects and distance < 0.5)) else original
        num = " ".join(tex).decode("utf-8").strip()
        fixme= []
        voies = []
        if num and adresses:
            for adr in adresses:
                adr = adr.decode("utf-8").strip()
                if adr.startswith(num + " "):
                    voies.append(adr[len(num):].strip())
        item = st_geometry_to_osm_primitive(geometry, osmfile)
        item.tags["source:date"] = str(update_date)
        item.tags["source"] = SOURCE_TAG
        item.tags["ref:FR:cadastre"] = numero_departement + ":" + str(object_rid)
        item.tags["addr:housenumber"] = num
        if len(voies) == 1:
            item.tags["addr:street"] = voies[0]
        elif len(voies) > 1:
            item.tags["addr:street"] = "|".join(voies)
            fixme.append(u"choisir la bonne rue: " + " ou ".join(voies))
        if (distance > 10) and (not intersects):
            num_parcelle = str(int(parcelle_idu[-4:]))
            fixme.append(str(int(distance)) + u" m de la parcelle n°" + num_parcelle + u": vérifier la position")
            fixme.reverse()
        if fixme: item.tags["fixme"] = " et ".join(fixme)
    #TODO: il faudrait aussi chercher les numéro contenus dans les
    # adresses des parcelles mais qui n'ont pas de correspondance dans
    # les points numvoie.
    corrige_addr_street(numero_departement, numero_commune, osmfile)

def corrige_addr_street(numero_departement, numero_commune, osmfile):
    # TODO
    pass

def main(args):
    parser = argparse.ArgumentParser(description="Export d'une commune au format .osm")
    parser.add_argument("departement", help="code departement", type=str)
    parser.add_argument("commune", help="code commune", type=int)
    args = parser.parse_args(args)
    departement  = normalise_numero_departement(args.departement)
    commune = normalise_numero_commune(args.commune)
    numero_insee = normalise_numero_insee(departement, commune)

    osmfile = OSMXMLFile()
    export_water(departement, commune, osmfile)
    osmfile.write(numero_insee + "-eau.osm")

    osmfile = OSMXMLFile()
    export_batiment(departement, commune, osmfile)
    osmfile.write(numero_insee + "-batiment.osm")

    osmfile = OSMXMLFile()
    export_cemeteries(departement, commune, osmfile)
    osmfile.write(numero_insee + "-cimetiere.osm")

    osmfile = OSMXMLFile(options={"upload":"false"})
    export_lieudit(departement, commune, osmfile)
    osmfile.write(numero_insee + "-lieudit.osm")

    osmfile = OSMXMLFile()
    export_petits_noms(departement, commune, osmfile)
    osmfile.write(numero_insee + "-petis-noms.osm")

    osmfile = OSMXMLFile()
    export_addr(departement, commune, osmfile)
    osmfile.write(numero_insee + "-adresse.osm")


if __name__ == '__main__':
    main(sys.argv[1:])
