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
Import the result segmented building prediction done by the script
pbf_segmented_building_predict.py
into the cadastre database.
"""


import sys
import json
import numpy
import os.path
import psycopg2
from shapely.geometry.polygon import Polygon
import numpy as np;

dbstring = file(os.path.join(os.path.dirname(sys.argv[0]), ".database-connection-string")).read()

db = psycopg2.connect(dbstring)
db.autocommit = True
cur = db.cursor()

def execute(query):
    print query
    return cur.execute(query)

def polygon_wkt(latlngs):
    # Restrict to 7 digits precision as in OSM database.
    return "POLYGON((" + ",".join(["%.7f %.7f" % tuple(ll) for ll in latlngs]) + "))"

def wkt_polygon_latlngs(wkt):
    assert(wkt.startswith("POLYGON((") and wkt.endswith("))"));
    coords = wkt[len("POLYGON(("): -len("))")];
    return [map(float,p.split(" ")) for p in  coords.split(",")]


def common_center_wkt(latlngs1, latlngs2):
    commons_points = set(map(tuple, latlngs1)).intersection(set(map(tuple, latlngs2)))
    center = map(numpy.mean, zip(*commons_points))
    return "POINT(%.7f %.7f)" % tuple(center)

def equals(latlngs1, latlngs2):
    if len(latlngs1) == len(latlngs2):
        diff = np.array(latlngs1) - np.array(latlngs2)
        return np.max(np.abs(diff)) < 0.0000001
    else:
        return False

def insert(data):
    id1 = data[0]['id']
    id2 = data[1]['id']
    assert(id1 < id2);
    latlngs1 = data[0]['latlngs']
    latlngs2 = data[1]['latlngs']
    already_exists = False
    execute("""
        SELECT id, ST_AsText(way1_geom), ST_AsText(way2_geom), resolution
        FROM segmented_cases 
        WHERE way1_osm_id = %s AND way2_osm_id = %s;
        """ % (id1, id2));
    for id, geom1, geom2, resolution in cur.fetchall():
        geom1 = wkt_polygon_latlngs(geom1)
        geom2 = wkt_polygon_latlngs(geom2)
        if equals(latlngs1, geom1) and equals(latlngs2, geom2):
            already_exists = True
        elif resolution == 'none':
            # The geometry of the building has changed,
            # mark the previous case as 'outofdate':
            execute("""
                UPDATE segmented_cases 
                SET resolution='outofdate', resolution_time=now()
                WHERE id=%s""" % id);
    if not already_exists:
        execute("""
            INSERT INTO segmented_cases 
                (way1_osm_id, way1_geom, way2_osm_id, way2_geom, center, creation_time) 
                VALUES (%d, ST_GeomFromText('%s', 4326), %d, ST_GeomFromText('%s', 4326), ST_GeomFromText('%s', 4326), now());
            """ % (id1, polygon_wkt(latlngs1), id2, polygon_wkt(latlngs2), common_center_wkt(latlngs1, latlngs2)))
    

def main(args):
    for line in sys.stdin.readlines():
        data = json.loads(line)
        insert(data)


if __name__ == '__main__':
    main(sys.argv[1:])

