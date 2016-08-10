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
Simplify -houses.osm file extracted from the cadastre by Qadastre2OSM program.

This simplification consists basicaly to merge close nodes and join nodes to near ways,
and to simplify ways as JOSM SimplifyWay action do (copied code).

Modified version of simplify_qadastre_houses.py
that try to fix invalid polygons.
PROBLEM: This code is twice slower than the original program.

"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.osm       import OsmParser, OsmWriter
from cadastre_fr.tools     import Timer
from cadastre_fr.simplify2 import simplify2
from cadastre_fr.simplify2 import OsmData
from cadastre_fr.globals   import VERBOSE


FIX_BROKEN_POLYGONS = True
MERGE_DISTANCE = 0.2 # 20 cm
JOIN_DISTANCE = 0.2 # 20 cm
SIMPLIFY_THRESHOLD = 0.1

def main(argv):
  args = argv[1:]
  merge_distance  = MERGE_DISTANCE
  join_distance = JOIN_DISTANCE
  simplify_threshold = SIMPLIFY_THRESHOLD
  fix_broken_polygons = FIX_BROKEN_POLYGONS
  global VERBOSE
  i = 0
  while i < (len(args) - 1):
    if args[i] == "-m":
      merge_distance = float(args[i+1])
      del(args[i:i+2])
    elif args[i] == "-j":
      join_distance = float(args[i+1])
      del(args[i:i+2])
    elif args[i] == "-s":
      simplify_threshold = float(args[i+1])
      del(args[i:i+2])
    elif args[i] == "-s":
      simplify_threshold = float(args[i+1])
      del(args[i:i+2])
    elif args[i] == "-v":
      VERBOSE=True
      del(args[i])
    elif args[i] == "-p":
      fix_broken_polygons=True
      del(args[i])
    else:
      i = i + 1
  if len(args) == 0 or len(args) > 2 or any([arg.startswith("-") for arg in args]):
      print("Simplify -houses.osm file extracted from the cadastre by Qadastre2OSM program")
      print("USAGE: %s [-v] [-p] [-m merge_distance] [-j join_distance] [-s simplify_threshold] input-houses.osm [output-houses.osm]" % argv[0])
      print("OPTIONS: -v    verbose")
      print("OPTIONS: -p    fix polygons")
      return -1
  else:
    input_filename = args[0]
    if len(args) > 1:
      output_filename = args[1]
    else:
      name,ext = os.path.splitext(input_filename)
      suffix = "-simplifie"
      if fix_broken_polygons:
          suffix = suffix + "-fix"
      output_filename = name + suffix + ext

    t=Timer("read")
    osm_data = OsmParser(OsmData).parse(input_filename)
    t.prnt()
    simplify2(osm_data, merge_distance, join_distance, simplify_threshold, fix_broken_polygons)
    t=Timer("save")
    OsmWriter(osm_data).write_to_file(output_filename)
    t.prnt()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

