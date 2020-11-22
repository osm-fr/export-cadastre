#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#


import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.osm import *

def capitalize(a):
  return " ".join([s.capitalize() for s in a.split(" ")])

if len(sys.argv) == 2:
    o = OsmParser().parse(sys.argv[1])
    for n in list(o.nodes.values()):
      if "name" in n.tags:
          n.tags["name"] = capitalize(n.tags["name"])
    OsmWriter(o).write_to_stream(sys.stdout)
else:
    print("ERROR: wrong number of arguments")
