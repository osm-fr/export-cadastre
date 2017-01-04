#!/usr/bin/env python
# -*- coding: utf-8 -*- 
#

"""
Return stats on contributors.

@param ip the ip adress of the contributor.

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


def get_stats(ip):
    dbstring = file(os.path.join(os.path.dirname(sys.argv[0]), ".database-connection-string")).read()
    db = psycopg2.connect(dbstring)
    cur = db.cursor()
    def e(query, args=None):
        query =  cur.mogrify(query, args)
        cur.execute(query)
        return cur.fetchone()[0];
    return dict(
        contributions_from_ip =
            e("SELECT count(*) FROM segmented_contributions WHERE ip = %s;", (ip,)),
        contributions_distinct_ips =
            e("SELECT count(distinct(ip)) FROM segmented_contributions;"),
        contributions =
            e("SELECT count(*) FROM segmented_contributions;"),
        contributions_distinct_cases =
            e("SELECT count(distinct(case_id)) FROM segmented_contributions;"),
        cases =
            e("SELECT count(*) FROM segmented_cases;"))

def main(args):
    parser = argparse.ArgumentParser(description='Get next segmente building cases to consider.')
    parser.add_argument("--ip", help="client ip address", type=str, default="127.0.0.1");
    args = parser.parse_args(args)
    print(json.dumps(get_stats(args.ip)));

if __name__ == '__main__':
    main(sys.argv[1:])



