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
Importe un fichier geojson (du cadastre) dans la base de donnée.

FIXME: DO UPDATE INSTEAD OF DELETE, INSERT

"""

import re
import sys
import json
import os.path
import datetime
import argparse

import db


def normalise_numero_commune(code):
    return "%03d" % (int(code),)

def normalise_numero_departement(code):
    code = str(code)
    while len(code) < 3: code = "0" + code
    assert re.match("^[0-9][0-9][0-9AB]$", code)
    return code

def get_tex_properties(properties):
    tex_ids = sorted([int(key[3:] or 0) for key in properties.keys() if key.startswith("TEX")])
    values = [properties["TEX%d" % i if (i>0) else "TEX"] for i in tex_ids]
    return [v.strip() for v in values if v]


def insert_sql(table, primary_values, other_values):
    db.execute("INSERT INTO %s (%s) VALUES (%s)" % (
                table,
                ", ".join(primary_values.keys() + other_values.keys()),
                ", ".join(["ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)" if k=="geometry" else "%s" for k in primary_values.keys() + other_values.keys()])),
            primary_values.values() + other_values.values())

def import_json_to_sql(jsonfile, departement):
    data = json.load(jsonfile if type(jsonfile) == file else open(jsonfile))
    departement = normalise_numero_departement(departement)
    assert data["type"] == "FeatureCollection"
    needDelete = True
    for item in data["features"]:
        primary_values = {}
        other_values = {}
        properties = item["properties"]
        print properties
        primary_values["departement"] = departement
        primary_values["object_rid"] = int(properties["OBJECT_RID"].replace("Objet_",""))
        other_values["geometry"] = json.dumps(item["geometry"])
        other_values["tex"] = get_tex_properties(properties)
        other_values["creat_date"] = datetime.datetime.strptime(str(properties["CREAT_DATE"]),"%Y%M%d").date()
        other_values["update_date"] = datetime.datetime.strptime(str(properties["UPDATE_DATE"]),"%Y%M%d").date()
        if item["layer"] == "batiment":
            other_values["dur"] = int(properties["DUR"] or 1)
        elif item["layer"] == "commune":
            other_values["idu"] = int(properties["IDU"])
        elif item["layer"] in ["tsurf", "tline"]:
            other_values["sym"] = int(properties["SYM"] or 0)
        elif item["layer"] == "parcelle":
            other_values["idu"] = str(properties["IDU"] or "")
            other_values["indp"] = int(properties["INDP"])
            other_values["supf"] = int(properties["SUPF"] or 0)
            other_values["coar"] = str(properties["COAR"] or "")
        elif item["layer"] == "numvoie":
            other_values["parcelle_idu"] = str(properties.get("PARCELLE_IDU") or "")
            other_values["parcelle_contains"] = bool(properties.get("PARCELLE_CONTAINS") or False)
        elif item["layer"] == "tronroute":
            other_values["rcad"] = str(properties["RCAD"] or "")
        elif item["layer"] in ["tronfluv", "lieudit", "voiep", "zoncommuni"]:
            pass # pas d'attributs suppl«mentaire
        else:
            print "ERROR: unsupported layer kind:", item["layer"]
            return False
        # TODO: update existing rather than delete all
        if needDelete:
            db.execute("DELETE from " + db.TABLE_PREFIX + item["layer"] + " WHERE departement=%s", [departement])
            needDelete = False
        insert_sql(db.TABLE_PREFIX + item["layer"], primary_values, other_values)
    db.db.commit();
    return True

def main(args):
    parser = argparse.ArgumentParser(description="Import un fichier cadastre geojson")
    parser.add_argument("departement", help="numéro departement", type=str)
    parser.add_argument('geojson', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    args = parser.parse_args(args)
    import_json_to_sql(args.geojson, normalise_numero_departement(args.departement))

if __name__ == '__main__':
    main(sys.argv[1:])
