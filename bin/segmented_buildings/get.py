#!/usr/bin/env python
# -*- coding: utf-8 -*- 
#

"""
Return a geoJSON file representing the next 
segmented building cases to consider for contributions.

@param ip the ip adress of the contributor.
@param limit max number of cases to return (integer).
@param lat latitude coordinates of the prefered location to look for new cases.
@param lon idem for longitude.

This file is largely derived from OpenSolarMap backend code from Christan Quest: 
https://github.com/opensolarmap/solback/blob/master/solback.py 
"""



import os
import sys
import json
import argparse
import psycopg2

DEFAULT_LAT=48.3
DEFAULT_LON=-1.8;

def get_cases(ip, limit, lat, lon):
    if limit>100: limit=100
    dbstring = file(os.path.join(os.path.dirname(sys.argv[0]), ".database-connection-string")).read()
    db = psycopg2.connect(dbstring)
    cur = db.cursor()
    results = []

    output_format = """
        '{"type":"Feature","id":'|| id::text
          ||',"properties":{'
          ||'"lat":'|| round(st_y(center)::numeric,7)::text
          ||',"lon":'|| round(st_x(center)::numeric,7)::text
          ||',"way1":'|| way1_osm_id::text 
          ||',"way2":'|| way2_osm_id::text 
          ||'},"geometry":{"type":"GeometryCollection","geometries":['
          ||st_asgeojson(way1_geom,7) || ','
          ||st_asgeojson(way2_geom,7) 
          ||']}}'"""

    query =  cur.mogrify("""
        SELECT """ + output_format + """
        FROM segmented_contributions_next n
        LEFT JOIN segmented_contributions co ON (co.case_id=n.case_id and co.ip=%s)
        JOIN segmented_cases ca ON (ca.id=n.case_id)
        WHERE n.total<10 AND co.ip is null
        GROUP BY ca.id, ca.way1_geom, ca.way2_geom, n.nb, n.last, ca.resolution
        HAVING resolution = 'none'
        ORDER BY n.nb desc, n.last limit %s;""", (ip, limit))
    cur.execute(query)
    rows = cur.fetchall()
    limit = limit - cur.rowcount

    if (limit > 0):
        # get cases around our location
        query =  cur.mogrify("""
            SELECT """ + output_format + """
            FROM segmented_cases ca
            LEFT JOIN segmented_contributions c1 ON (id=c1.case_id and c1.ip=%s)
            LEFT JOIN segmented_contributions c2 ON (id=c2.case_id)
            LEFT JOIN segmented_contributions_next n ON (n.case_id=ca.id AND n.nb>=0)
            WHERE ca.resolution = 'none'
            AND coalesce(n.total,0)<10 AND c1.ip IS NULL
            GROUP by id, center, n.nb, n.last
            HAVING (count(c2.*)<10 or (count(distinct(c2.choice))=1 AND count(c2.*)<=3))
            ORDER BY ST_Distance(center,ST_SetSRID(ST_MakePoint(%s, %s),4326))/(coalesce(n.nb,0)*10+1)
            LIMIT %s;""", (ip, lon, lat, limit))
        cur.execute(query)
        limit = limit - cur.rowcount
        rows.extend(cur.fetchall())
    return dict(count=len(rows), type="FeatureCollection", features=[json.loads(r[0]) for r in rows])

def main(args):
    parser = argparse.ArgumentParser(description='Get next segmente building cases to consider.')
    parser.add_argument("--ip", help="client ip address", type=str, default="127.0.0.1");
    parser.add_argument("--limit", help="max results nb to return", type=int, default=1);
    parser.add_argument("--lat", help="latitude", type=float, default=DEFAULT_LAT);
    parser.add_argument("--lon", help="longitude", type=float, default=DEFAULT_LON);
    args = parser.parse_args(args)
    print(json.dumps(get_cases(args.ip, args.limit, args.lat, args.lon)));

if __name__ == '__main__':
    main(sys.argv[1:])



