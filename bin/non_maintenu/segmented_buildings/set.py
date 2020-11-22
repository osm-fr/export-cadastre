#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Record a contribution for the validation of segmented building cases.

Possible choices are 'join' 'keep' 'unknown'.
The special choice  'back' allow to delete a previous contribution.

@param ip the ip adress of the contributor that made the validation
@param id the id of the segmentation cases validated.
@param choice 'join' | 'keep' | 'unknown' | 'back'.
@param session a random 32 bit integer that need to match for 'back' choice.

"""


import os
import sys
import json
import argparse
import psycopg2


def set_contribution(ip, id, choice, session):
    dbstring = file(os.path.join(os.path.dirname(sys.argv[0]), ".database-connection-string")).read()
    db = psycopg2.connect(dbstring)
    db.autocommit = True
    cur = db.cursor()

    if choice in ['back', 'join', 'keep', 'unknown']:
        query = cur.mogrify("""
            DELETE FROM segmented_contributions
            WHERE case_id=%s AND ip=%s AND session=%s
            AND (now() - "time") < (interval '10 minute')""",
                (id, ip, session))
        cur.execute(query)
        if choice != 'back':
            cur.execute(query)
            query = cur.mogrify("""
                INSERT INTO segmented_contributions
                (case_id, ip, "time", choice, session)
                VALUES (%s, %s, now(), %s, %s);""", (id, ip, choice, session))
            cur.execute(query)
    else:
        sys.exit(-1)

def main(args):
    parser = argparse.ArgumentParser(description='Record a contribution.')
    parser.add_argument("--ip", help="client ip address", type=str, default="127.0.0.1");
    parser.add_argument("--id", help="segmentation case id", type=int, required=True);
    parser.add_argument("--choice", help="choice", type=str, required=True);
    parser.add_argument("--session", help="sesison random intereg", type=int, default=0);
    args = parser.parse_args(args)
    set_contribution(args.ip, args.id, args.choice, args.session);

if __name__ == '__main__':
    main(sys.argv[1:])

