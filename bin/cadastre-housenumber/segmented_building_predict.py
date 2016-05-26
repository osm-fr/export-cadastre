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

Utilise le classifier généré par segmented_building_classifier.py
pour détecter si des buildings doivent êtrefusionnés.

"""


import re
import sys
import copy
import math
import numpy
import pickle
import os.path
import operator
import itertools
from sklearn                        import svm

from osm                            import Osm,Node,Way,Relation,OsmParser,OsmWriter
from simplify_qadastre_houses       import simplify
from simplify_qadastre_houses       import get_centered_metric_equirectangular_transformation
from segmented_building_find_joined import compute_transformed_position_and_annotate
from segmented_building_classifier  import get_segmented_analysis_vector_from_osm
from segmented_building_classifier  import get_external1_common_external2_ways
from pdf_vers_osm_housenumbers      import Point

VERBOSE=False

def main(argv):
  args = argv[1:]
  global VERBOSE
  i = 0
  while i < (len(args) - 1):
    if args[i] == "-v":
      VERBOSE=True
      del(args[i])
    else:
      i = i + 1
  if len(args) == 0 or len(args) > 2 or any([arg.startswith("-") for arg in args]):
      return print_usage("wrong argument")
      return -1
  else:
    input_filename = args[0]
    if len(args) > 1:
      output_filename = args[1]
    else:
      name,ext = os.path.splitext(input_filename)
      output_filename = name + "-prediction_segmente" + ext

    if VERBOSE: print "load " + input_filename + " ..."

    osm = OsmParser().parse(input_filename)
    #simplify(osm, 0.2, 0.2, 0.1)

    if VERBOSE: print "transform..."
    inputTransform, outputTransform = get_centered_metric_equirectangular_transformation(osm)
    compute_transformed_position_and_annotate(osm, inputTransform)

    if VERBOSE: print "detect..."
    buildings = get_predicted_segmented_buildings(osm, get_classifier())
    if VERBOSE: print " -> ", len(buildings), "cas"

    output_osm = filter_buildings_junction(osm, buildings)
    
    if VERBOSE: print "save ", output_filename 
    OsmWriter(output_osm).write_to_file(output_filename)

    return 0


def get_classifier():
    segmented_data_dir=os.path.join(os.path.dirname(sys.argv[0]), "segmented_building_data")
    os.system("cd " + segmented_data_dir  +"; make -s")
    classifier = pickle.load(open(os.path.join(segmented_data_dir, "classifier.pickle")))
    return classifier



def get_predicted_segmented_buildings(osm_data, classifier):
    buildings = []
    segmented_buildings_couples = []
    for way in osm_data.ways.itervalues():
        if way.isBuilding:
            buildings.append(way)
            way.isJoined = way.tags.get("joined") not in (None, "?", "no")
            way.hasWall = way.tags.get("wall") != "no" # default (None) is yes
    for rel in osm_data.relations.itervalues():
        if rel.isBuilding:
            rel.isJoined = rel.tags.get("joined") not in (None, "?", "no")
            rel.hasWall = rel.tags.get("wall") != "no" # default (None) is yes
            for item, role in osm_data.iter_relation_members(rel):
                if item != None: # not downloaded
                    if role in ("inner", "outer"):
                        item.hasWall = rel.hasWall
                        item.isJoined = rel.isJoined
                        if "joined" in rel.tags:
                            item.tags["joined"] = rel.tags["joined"]
                        buildings.append(item)
    number = 0
    for building in buildings:
        nodes = [osm_data.nodes[i] for i in building.nodes]
        ways_id = reduce(operator.or_, [node.ways for node in nodes], set())
        ways = [osm_data.ways[i] for i in ways_id if i != building.id()]
        for way in ways:
            if way.isBuilding and way.hasWall == building.hasWall and way.id() > building.id():
                vector1 = get_segmented_analysis_vector_from_osm(osm_data, building, way)
                vector2 = get_segmented_analysis_vector_from_osm(osm_data, way, building)
                if (vector1 != None and classifier.predict(vector1) == [1]) or \
                   (vector2 != None and classifier.predict(vector2) == [1]):
                   segmented_buildings_couples.append( (building, way) )
    return segmented_buildings_couples


def filter_buildings_junction(osm_data, buildings_couples):
    osm = Osm({'upload':'false'})
    for b1, b2 in buildings_couples:
        external1, common, external2 = get_external1_common_external2_ways(b1.nodes, b2.nodes)
        for node_id in common:
            node = osm_data.nodes[node_id]
            node.tags["fixme"] = u"Est-ce que les bâtiments ne sont pas segmentés ici par le cadastre ?"
            if node_id not in osm.nodes:
                osm.add_node(node)
        way = Way({})
        way.nodes = common
        way.tags["name"] = u"Est-ce que les bâtiments ne sont pas segmentés ici par le cadastre ?"
        osm.add_way(way)
    return osm

def print_usage(error=""):
    if error: print "ERROR:", error
    print "USAGE: %s houses.osm" % (sys.argv[0],)
    if error:
        return -1
    else:
        return 0

    
if __name__ == '__main__':
    sys.exit(main(sys.argv))

