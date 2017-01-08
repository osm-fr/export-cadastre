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
Force resolution for a given case.
"""

import sys
import os.path
import psycopg2
import argparse

dbstring = file(os.path.join(os.path.dirname(sys.argv[0]), ".database-connection-string")).read()
db = psycopg2.connect(dbstring)
db.autocommit = True
cur = db.cursor()

def main(args):
    parser = argparse.ArgumentParser(description='Force resolution for a given case.')
    parser.add_argument("id", help="case id", type=int)
    parser.add_argument("resolution", choices=['join', 'keep', 'unknown', 'outofdate'])
    args = parser.parse_args(args)
    cur.execute(cur.mogrify("""
        UPDATE segmented_cases 
        SET resolution=%s, resolution_time=now() 
        WHERE id=%s""", (args.resolution, args.id)));

if __name__ == '__main__':
    main(sys.argv[1:])

