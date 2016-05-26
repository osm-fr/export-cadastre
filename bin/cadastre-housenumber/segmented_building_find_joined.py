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
Compare deux fichiers .osm pour trouver les buildings du premier
qui sont fusionés dans le deuxième.
Génère un trosième fichier, copie du premier avec un nouveau tag
"joined" contenant l'id de building fusionné dans le deuxième.
(ou "no" si non fusioné ou "?" si building pas clairement trouvé 
dans le deuxième fichier)
"""


import re
import sys
import cv2
import copy
import math
import numpy
import os.path
import operator
import itertools
import rtree.index
from glob import glob
from matplotlib                     import pyplot
from shapely.geometry.polygon       import Polygon
from shapely.geometry.linestring    import LineString
from shapely.geometry.point         import Point
import shapely.affinity

from osm                            import Osm,Node,Way,Relation,OsmParser,OsmWriter
from pdf_vers_osm_housenumbers      import CadastreParser
from pdf_vers_osm_housenumbers      import CadastreToOSMTransform
from cadastre_vers_osm_adresses     import SOURCE_TAG
from simplify_qadastre_houses       import simplify
from simplify_qadastre_houses       import get_centered_metric_equirectangular_transformation


TOLERANCE = 0.5 # distance en metre de tolérance du buffer pour considérer un building inclus dans un autre
#IMG_SIZE = 256


def main(argv):
    if len(argv) == 2 and len(argv[1]) == 5:
        prefix = argv[1]
        if os.path.exists(prefix + "-houses-simplifie.osm"):
            segmented_osm_file = prefix + "-houses-simplifie.osm"
        elif os.path.exists(prefix + "-houses.osm"):
            segmented_osm_file = prefix + "-houses.osm"
        else:
            return print_usage("no prefix-houses.osm file found")
        if os.path.exists(prefix + "-buildings.osm"):
            corrected_osm_file = prefix + "-buildings.osm"
        else:
            return print_usage("no prefix-buildings.osm file found")
        other_args = []
    else:
        osm_args = [f for f in argv[1:] if os.path.splitext(f)[1] == ".osm"]
        if len(osm_args) == 2:
            segmented_osm_file,  corrected_osm_file  = osm_args 
        elif len(osm_args) < 2:
            return print_usage("not enough .osm arguments")
        else:
            return print_usage("too many .osm arguments")
        other_args = [f for f in argv[1:] if os.path.splitext(f)[1] not in (".osm")]
        if len(other_args) != 0:
            return print_usage("invalid argument: " + other_args[0])
        prefix = os.path.commonprefix(osm_args)
    print "load " + segmented_osm_file
    segmented_osm = OsmParser().parse(segmented_osm_file)
    print "load " + corrected_osm_file
    corrected_osm = OsmParser().parse(corrected_osm_file)
    print "find joined buildings"
    #joined, unmodified =
    find_joined_and_unmodified_buildings(segmented_osm, corrected_osm, TOLERANCE)
    #joined_osm     = osm_filter_items(segmented_osm, itertools.chain(*joined))
    #unmodified_osm = osm_filter_items(segmented_osm, unmodified)
    #OsmWriter(joined_osm).write_to_file(os.path.splitext(corrected_osm_file)[0] + "-joined.osm")
    #OsmWriter(unmodified_osm).write_to_file(os.path.splitext(corrected_osm_file)[0] + "-unmodified.osm")
    output_file = os.path.splitext(segmented_osm_file)[0] + "-joined.osm"
    print "save " + output_file
    OsmWriter(segmented_osm).write_to_file(output_file)
    return 0

def print_usage(error=""):
    if error: print "ERROR:", error
    print "USAGE: %s houses-segmente.osm buildings-corrected.osm" % (sys.argv[0],)
    if error:
        return -1
    else:
        return 0


def find_joined_and_unmodified_buildings(segmented_osm, corrected_osm, tolerance):
    """Find buildings from segmented_osm osm representation that
       have either been joined or unmodified in corrected_osm"""
    for cadastre_way in itertools.chain(segmented_osm.ways.itervalues(), segmented_osm.relations.itervalues()):
        cadastre_way.isJoined = False
    inputTransform, outputTransform = get_centered_metric_equirectangular_transformation(segmented_osm)
    compute_transformed_position_and_annotate(segmented_osm, inputTransform)
    compute_transformed_position_and_annotate(corrected_osm, inputTransform)
    compute_buildings_polygons_and_rtree(segmented_osm, tolerance)
    compute_buildings_polygons_and_rtree(corrected_osm, tolerance)
    segmented_rtree = segmented_osm.buildings_rtree
    corrected_rtree = corrected_osm.buildings_rtree
    joined_buildings = []
    unmodified_buildings = []
    for segmented_way in itertools.chain(segmented_osm.ways.itervalues(), segmented_osm.relations.itervalues()):
        if segmented_way.isBuilding and ("joined" not in segmented_way.tags):
            segmented_way.tags["joined"] = "?"
            for corrected_way in [corrected_osm.get(e.object) for e in corrected_rtree.intersection(segmented_way.bbox, objects=True)]:
                if corrected_way.isBuilding:
                    if ways_equals(segmented_way, corrected_way, tolerance):
                        unmodified_buildings.append(segmented_way)
                        segmented_way.tags["joined"] = "no"
                    elif corrected_way.tolerance_polygon.contains(segmented_way.polygon):
                        composed_tolerance_polygon = segmented_way.tolerance_polygon
                        composed_ways = [segmented_way]
                        for segmented_way2 in [segmented_osm.get(e.object) for e in segmented_rtree.intersection(corrected_way.bbox, objects=True)]:
                            if segmented_way.tags.get("wall") == segmented_way2.tags.get("wall"):
                              if corrected_way.tolerance_polygon.contains(segmented_way2.polygon):
                                composed_tolerance_polygon = composed_tolerance_polygon.union(segmented_way2.tolerance_polygon)
                                composed_ways.append(segmented_way2)
                        if composed_tolerance_polygon.contains(corrected_way.polygon):
                            joined_buildings.append(composed_ways)
                            for way in composed_ways:
                                way.tags["joined"] = corrected_way.textid()
                                way.isJoined = True
    return joined_buildings, unmodified_buildings


def compute_transformed_position_and_annotate(osm_data, transform):
    for node in osm_data.nodes.itervalues():
        node.ways = set()
        node.relations = set()
        node.position = transform.transform_point(
            (node.lon(), node.lat()))
    for way in osm_data.ways.itervalues():
        way.relations = set()
    for rel in osm_data.relations.itervalues():
        rel.relations = set()
    for rel in osm_data.relations.itervalues():
       for rtype,rref,rrole in rel.itermembers():
          if rtype == "way":
              if rref in osm_data.ways:
                osm_data.ways[rref].relations.add(rel.id())
          if rtype == "node":
              if rref in osm_data.nodes:
                osm_data.nodes[rref].relations.add(rel.id())
          if rtype == "relation":
              if rref in osm_data.relations:
                osm_data.relations[rref].relations.add(rel.id())
    for way in osm_data.ways.itervalues():
        for node_id in way.nodes:
            node = osm_data.nodes[node_id]
            node.ways.add(way.id())
        way.isBuilding = way.tags.get("building") not in (None, "no")
        if way.isBuilding:
            way.hasWall = way.tags.get("wall") != "no" # default (None) is yes
    for rel in osm_data.relations.itervalues():
        rel.isBuilding = (rel.tags.get("type") == "multipolygon") and (rel.tags.get("building") not in (None, "no"))
        if rel.isBuilding:
            rel.hasWall = rel.tags.get("wall") != "no" # default (None) is yes

def compute_buildings_polygons_and_rtree(osm_data, tolerance):
    buildings_rtree = rtree.index.Index()
    osm_data.buildings_rtree = buildings_rtree 
    for way in osm_data.ways.itervalues():
        if way.isBuilding:
            if len(way.nodes) >= 3:
               way.polygon = Polygon([osm_data.nodes[i].position for i in way.nodes])
            else:
               way.polygon = LineString([osm_data.nodes[i].position for i in way.nodes])
            way.bbox = way.polygon.bounds
            way.tolerance_polygon = way.polygon.buffer(tolerance)
            buildings_rtree.insert(way.id(), way.bbox, way.textid())
    for rel in osm_data.relations.itervalues():
        if rel.isBuilding:
            exterior = None
            interiors = []
            for rtype,rref,rrole in rel.itermembers():
                if rtype == "way":
                    way = osm_data.ways[rref]
                    if rrole == "outer":
                        exterior = [osm_data.nodes[i].position for i in way.nodes]
                    elif rrole == "inner":
                        interiors.append([osm_data.nodes[i].position for i in way.nodes])
            rel.polygon = Polygon(exterior, interiors)
            rel.bbox = rel.polygon.bounds
            rel.tolerance_polygon = rel.polygon.buffer(tolerance)
            buildings_rtree.insert(rel.id(), rel.bbox, rel.textid())


def ways_equals(way1, way2, tolerance):
    bbox_diff = max(map(abs, map(operator.sub, way1.bbox, way2.bbox)))
    return (bbox_diff < tolerance) and \
        way1.tolerance_polygon.contains(way2.polygon) and \
        way2.tolerance_polygon.contains(way1.polygon)



    
if __name__ == '__main__':
    sys.exit(main(sys.argv))

