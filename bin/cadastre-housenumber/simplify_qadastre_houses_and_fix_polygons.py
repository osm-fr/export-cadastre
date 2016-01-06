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


import sys
import copy
import math
import os.path
import operator
import traceback
import rtree.index
from shapely.ops import polygonize
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry.polygon import Polygon
from shapely.geometry.polygon import LinearRing
from shapely.geometry.polygon import LineString
from shapely.geometry.multipolygon import MultiPolygon
import shapely.geos
import timeit

#sys.path.append("../../cadastre-openstreetmap-fr/")

from osm import Osm, Node, Way, Relation, OsmParser, OsmWriter
from pdf_vers_osm_housenumbers import BoundingBox, LinearTransform, Point
from cherche_osm_buildings import orthoprojection_on_segment_ab_of_point_c


FIX_BROKEN_POLYGONS = True
MERGE_DISTANCE = 0.2 # 20 cm
JOIN_DISTANCE = 0.2 # 20 cm
SIMPLIFY_THRESHOLD = 0.1
VERBOSE=False

EARTH_RADIUS_IN_METTER = 6371000
EARTH_CIRCUMFERENCE_IN_METTER = 2*math.pi*EARTH_RADIUS_IN_METTER

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
    simplify(osm_data, merge_distance, join_distance, simplify_threshold, fix_broken_polygons)
    t=Timer("save")
    OsmWriter(osm_data).write_to_file(output_filename)
    t.prnt()
    return 0


def simplify(osm_data, merge_distance, join_distance, simplify_threshold, fix_broken_polygons):

  t=Timer("remove_duplicated_nodes_in_ways")
  remove_duplicated_nodes_in_ways(osm_data)
  t.prnt()

  t=Timer("merge_close_nodes")
  merge_close_nodes(osm_data, merge_distance, False)
  t.prnt()

  t=Timer("simplify_ways")
  simplify_ways(osm_data, simplify_threshold)
  t.prnt()

  t=Timer("ways_rtree ")
  ways_rtree = compute_ways_rtree(osm_data)
  t.prnt()

  t=Timer("join_close_nodes")
  join_close_nodes(osm_data, ways_rtree, join_distance)
  t.prnt()

  t=Timer("merge_close_nodes")
  merge_close_nodes(osm_data, simplify_threshold, True)
  t.prnt()

  t=Timer("compute_ways_polygons")
  compute_ways_polygons(osm_data, ways_rtree)
  t.prnt()

  if fix_broken_polygons:
      t=Timer("fix_ways_polygons")
      fix_ways_polygons(osm_data, simplify_threshold*simplify_threshold, ways_rtree)
      t.prnt()
      t=Timer("ways_rtree ")
      ways_rtree = compute_ways_rtree(osm_data)
      t.prnt()
      t=Timer("join_close_nodes")
      join_close_nodes(osm_data, ways_rtree, join_distance)
      t.prnt()
      t=Timer("merge_close_nodes")
      merge_close_nodes(osm_data, simplify_threshold, True)
      t.prnt()

  t=Timer("remove_inside_ways")
  remove_inside_ways(osm_data, ways_rtree)
  t.prnt()

  t=Timer("remove_identical_ways")
  remove_identical_ways(osm_data)
  t.prnt()



def get_centered_metric_equirectangular_transformation(bbox):
  """ return a Transform from OSM data WSG84 lon/lat coordinate system
      to an equirectangular projection centered on the center of the data,
      with a unit ~ 1 meter at the center
  """
  bbox = BoundingBox(*bbox)
  center = bbox.center()
  bb1 = (center.x, center.y, center.x + 360, center.y + 360)
  bb2 = (0, 0, EARTH_CIRCUMFERENCE_IN_METTER*math.cos(center.y*math.pi/180), EARTH_CIRCUMFERENCE_IN_METTER)
  inputTransform = LinearTransform(bb1, bb2)
  outputTransform = LinearTransform(bb2, bb1)
  return inputTransform, outputTransform


def merge_close_nodes(osm_data, max_distance, can_merge_same_way):
    """Merge nodes that are close to one another while not being members of the same ways.

       We assume nodes are not part of relations
       and that nodes are part of the ways which ids are listed in node's .ways set attribute
       We assume that the ways are closed
    """
    replaced = set()
    for node in osm_data.nodes.values():
        node_id = node.id()
        if node_id not in replaced:
            p = node.position
            search_bbox = p.x - max_distance, p.y - max_distance, \
                            p.x + max_distance, p.y + max_distance
            best_node = None
            best_distance = max_distance
            for near_node in osm_data.search_nodes(search_bbox):
                if near_node.id() != node_id:
                    distance = node.position.distance(near_node.position)
                    if (distance < best_distance) and can_merge_nodes(osm_data, node, near_node, can_merge_same_way):
                          best_node = near_node
                          best_distance = distance
            if best_node:
                if not hasattr(node, "min_angle"):
                    node.min_angle = min_node_angle(osm_data, node)
                if not hasattr(best_node, "min_angle"):
                    best_node.min_angle = min_node_angle(osm_data, best_node)
                if node.min_angle < best_node.min_angle:
                    osm_data.replace_node(best_node, node)
                    replaced.add(best_node.id())
                else:
                    osm_data.replace_node(node, best_node)
        

def can_merge_nodes(osm_data, n1, n2, can_merge_same_way):
    result = True
    same_ways = n1.ways & n2.ways
    #if len(same_ways) > 0:
    #    if can_merge_same_way:
    #        for way_id in same_ways:
    #            way = osm_data.ways[way_id]
    #            n1_previous, n1_following = way.get_previous_and_next_node(n1)
    #            if (n2 != n1_previous) and (n2 != n1_following):
    #                result = False
    #                pass
    #    else:
    #        result = False
    result = (len(same_ways)) == 0 or can_merge_same_way
    return result


def compute_ways_rtree(osm_data):
    ways_rtree = rtree.index.Index()
    for way in osm_data.ways.values():
        add_to_ways_rtree(osm_data, ways_rtree, way)
    return ways_rtree

def add_to_ways_rtree(osm_data, ways_rtree, way):
        bbox = BoundingBox.of_points([osm_data.nodes[node_id].position for node_id in way.nodes])
        way.bbox = [bbox.x1,bbox.y1,bbox.x2, bbox.y2]
        ways_rtree.insert(way.id(), way.bbox, way.id())


def join_close_nodes(osm_data, ways_rtree, distance):
    """Join nodes to close ways."""
    for node in osm_data.nodes.values():
        node_id = node.id()
        position = node.position
        search_bounds = position.x-distance, position.y - distance, \
                        position.x + distance, position.y + distance
        closest_way = None
        closest_position = None
        closest_distance = distance
        closest_index = None
        for result in ways_rtree.intersection(search_bounds, objects=True):
            way_id = result.object
            way = osm_data.ways[way_id]
            if can_join_node_to_way(node, way):
                node = osm_data.nodes[node_id]
                i = 0
                for i in xrange(len(way.nodes) - 1):
                    n1 = osm_data.nodes[way.nodes[i]]
                    n2 = osm_data.nodes[way.nodes[i+1]]
                    if can_join_node_to_segment(osm_data, node, n1, n2):
                        p1 = n1.position
                        p2 = n2.position
                        p = orthoprojection_on_segment_ab_of_point_c(p1,p2, node.position)
                        if (p !=None) and (node.position.distance(p) < closest_distance):
                          closest_distance = node.position.distance(p)
                          closest_way = way
                          closest_index = i+1
                          closest_position = Point(p[0],p[1])
        if closest_way:
            if VERBOSE: print "Join node ", node_id, " to way ", closest_way.id()
            closest_way.nodes.insert(closest_index, node_id)
            node.ways.add(closest_way.id())
            osm_data.move_node(node, closest_position)
            # It is possible that the segment we join (n1,n2) is part
            # of more than one other way, so in theory we should insert 
            # the node in all of them, but we do not as this is necessariy
            # an invaid situation that will raise an error in JOSM.


def can_join_node_to_way(node, way):
   # Don't join to the same way:
   return node.id() not in way.nodes


def can_join_node_to_segment(osm_data, node, n1, n2):
    result = True
    node_ways_relations = reduce(operator.or_, [osm_data.ways[way_id].relations for way_id in node.ways])
    for way_id in (n1.ways & n2.ways):
        way = osm_data.ways[way_id]
        n1_previous, n1_next = way.get_previous_and_next_node(n1)
        if n2.id() == n1_previous or n2.id() == n1_next:
            # the segment n1, n2 is directly part of 'way' (without making a longer path)
            if way_id in node.ways:
                # node is member of the same way as the segment 
                result = False
                break
            if len(node_ways_relations & way.relations) != 0:
                # node's way are member of a common relation (i.e multipolygon)
                result = False
                break
    return result


def remove_inside_ways(osm_data, ways_rtree):
    for way1 in osm_data.ways.values():
        if len(way1.relations) == 0:
          polygon1 =  way1.polygon
          if polygon1.is_valid:
              others_polygon = None
              for way2_id in [e.object for e in ways_rtree.intersection(way1.bbox, objects=True)]:
                  way2 = osm_data.ways[way2_id]
                  if (way2_id != way1.id()) and (len(way2.relations) == 0) and (("wall" in way1.tags) or ("wall" not in way2.tags)):
                      polygon2 =  way2.polygon
                      if polygon2.is_valid:
                          if others_polygon == None:
                             others_polygon = polygon2
                          else:
                             area1 = others_polygon.area
                             others_polygon = others_polygon.union(polygon2)
              if others_polygon != None and others_polygon.buffer(0.1).contains(polygon1):
                  if VERBOSE: print "way ", way1.id(), " inside ", way2_id
                  ways_rtree.delete(way1.id(), way1.bbox)
                  osm_data.delete_way(way1)

def way_center(way):
    bbox = way.bbox
    return ((bbox[0] + bbox[2] * 0.5), (bbox[1] + bbox[3]) * 0.5)


def fix_invalid_polygon(p):
    if not p.is_valid:
        p_buffer_0 = p.buffer(0)
        # If the polygon cross itself the .buffer(0) operation
        # will return only half of the polygon (the other half
        # may be considered negative)
        # This is not what we want, so we check resulting area 
        # to detect this didn't happen:
        if p_buffer_0.area >= p.area*0.99:
            p = p_buffer_0
        else:
            # Compute the list of all segments of the polygon, add  missing points
            # at the position they cross each others, and use
            # polygonize() tool function to rebuild a MultiPolygon
            assert(len(p.interiors) == 0)
            coords = p.exterior.coords
            segments = [ LineString([coords[i], coords[i+1]]) for i in xrange(len(coords)-1)]
            crosses = [set() for i in xrange(len(segments))]
            for i in xrange(len(segments)):
                for j in xrange(i):
                  if segments[i].crosses(segments[j]):
                      intersection = segments[i].intersection(segments[j])
                      assert(type(intersection)== ShapelyPoint)
                      intersection = intersection.coords[0]
                      crosses[i].add(intersection)
                      crosses[j].add(intersection)
            result_segments = []
            for i in xrange(len(segments)):
                if crosses[i]:
                    points = list(crosses[i])
                    points.sort(key = lambda c : ShapelyPoint(segments[i].coords[0]).distance(ShapelyPoint(c)))
                    points = [segments[i].coords[0]] + points + [segments[i].coords[1]]
                    for j in xrange(len(points) - 1):
                        result_segments.append((points[j], points[j+1]))
                else:
                    result_segments.append((segments[i].coords[0], segments[i].coords[1]))
            p = MultiPolygon(list(polygonize(result_segments)))
    return p


def filter_polygon_interior_bigger_than(polygon, min_area):
    modified  = False
    interiors = []
    for i in polygon.interiors:
        if Polygon(i).area >= min_area:
          interiors.append(i)
        else:
            modified = True
    if modified:
        return Polygon(polygon.exterior, inetriors)
    else:
        return polygon


def get_polygon_list_bigger_than(polygon, min_area):
    if type(polygon) == MultiPolygon:
        polygons = list(polygon.geoms)
    else:
        polygons = [polygon]
    result = []
    for p in polygons:
        if len(p.interiors) == 0:
            if p.area >= min_area:
                result.append(p)
        elif Polygon(p.exterior).area >= min_area:
            result.append(filter_polygon_interior_bigger_than(p, min_area))
    return result


def compute_ways_polygons(osm_data, ways_rtree):
    for way in osm_data.ways.values():
        if len(way.nodes) > 2:
            way.polygon = Polygon([(osm_data.nodes[i].position[0],osm_data.nodes[i].position[1]) for i in way.nodes])
        else:
            ways_rtree.delete(way.id(), way.bbox)
            osm_data.delete_way(way)


def fix_ways_polygons(osm_data, min_area, ways_rtree):
    for original_way in osm_data.ways.values():
        if not original_way.polygon.is_valid:
            try:
                if VERBOSE: print "fix invalid way: ", original_way.id()
                position_hash = {(original_way.polygon.exterior.coords[i][0],original_way.polygon.exterior.coords[i][1]) : original_way.nodes[i] for i in range(len(original_way.nodes))}
                polygon = fix_invalid_polygon(original_way.polygon)
                first = True
                original_nodes = copy.deepcopy(original_way.nodes)
                original_tags = copy.deepcopy(original_way.tags)
                ways_rtree.delete(original_way.id(), original_way.bbox)
                polygons = get_polygon_list_bigger_than(polygon, min_area)
                if len(polygons) > 0:
                    for polygon in polygons:
                        if first:
                           outer_way = original_way
                        else:
                           outer_way = osm_data.create_way({}, copy.deepcopy(original_tags))
                        outer_way.polygon = polygon
                        if polygon.interiors:
                           # This has created a multipolygon
                           if outer_way.relations:
                               raise Exception("Unsupported situation")
                           relation = osm_data.create_relation({}, {"type": "multipolygon"})
                           for key,val in outer_way.tags.items():
                               if key !="source":
                                   relation.tags[key] = val
                                   del(outer_way.tags[key])
                           relation.add_member(outer_way, "outer")
                           for interior in polygon.interiors:
                               interior_polygon = Polygon(interior)
                               inner_way = osm_data.create_way({}, {})
                               inner_way.polygon = interior_polygon
                               relation.add_member(inner_way, "inner")
                               if "source" in original_tags: 
                                   inner_way.tags["source"] = original_tags["source"]
                               for position in interior.coords:
                                   position = tuple(position)
                                   if position in position_hash:
                                       node_id = position_hash[position]
                                       node = osm_data.nodes[node_id]
                                   else:
                                       node = osm_data.create_node_at_xy(position)
                                       node_id = node.id()
                                       position_hash[position] = node_id
                                       node.ways.add(way.id())
                                   inner_way.add_node(node)
                               add_to_ways_rtree(osm_data, ways_rtree, inner_way)
                        outer_way.nodes = []
                        for position in polygon.exterior.coords:
                           position = tuple(position)
                           if position in position_hash:
                               node_id = position_hash[position]
                               node = osm_data.nodes[node_id]
                           else:
                               node = osm_data.create_node_at_xy(position)
                               node_id = node.id()
                               position_hash[position] = node_id
                           outer_way.add_node(node)
                        if first:
                            for node_id in (set(original_nodes) - set(outer_way.nodes)):
                                node = osm_data.nodes[node_id]
                                node.ways.remove(original_way.id())
                                if len(node.ways) == 0:
                                    osm_data.delete_node(node)
                                first = False
                        add_to_ways_rtree(osm_data, ways_rtree, outer_way)
                else:
                    ways_rtree.delete(original_way.id(), original_way.bbox)
                    osm_data.delete_way(original_way)
            except:
                print traceback.format_exc()


def simplify_ways(osm_data, threshold):
    for way in osm_data.ways.values():
        nodes = [osm_data.nodes[node_id] for node_id in way.nodes]
        for node_sublist in split_node_list_at_required_nodes(osm_data, nodes):
            keeped_nodes = buildSimplifiedNodeSet(node_sublist, 0, len(node_sublist)-1, threshold)
            for n in node_sublist:
                if n.id() not in keeped_nodes:
                  osm_data.delete_node(n)
        if len(way.nodes) <= 3:
            osm_data.delete_way(way)


def buildSimplifiedNodeSet(nodes, fromIndex, toIndex, threshold):
    # taken from SimplifyWay.java of JOSM
    result = set() # the set of nodes to keep
    fromN = nodes[fromIndex]
    toN = nodes[toIndex]
    # Get max xte
    imax = -1
    xtemax = 0.0
    for i in xrange(fromIndex+1, toIndex):
        n = nodes[i]
        xte = abs(EARTH_RADIUS_IN_METTER
                    * xtd(fromN.lat() * math.pi / 180, fromN.lon() * math.pi / 180, toN.lat() * math.pi
                            / 180, toN.lon() * math.pi / 180, n.lat() * math.pi / 180, n.lon() * math.pi
                            / 180))
        if xte > xtemax:
            xtemax = xte
            imax = i
    if (imax != -1) and  (xtemax >= threshold):
        # Segment cannot be simplified - try shorter segments
        result.update(buildSimplifiedNodeSet(nodes, fromIndex, imax, threshold))
        result.update(buildSimplifiedNodeSet(nodes, imax, toIndex, threshold))
    else:
        result.add(fromN.id())
        result.add(toN.id())
    return result

def xtd(lat1, lon1, lat2, lon2, lat3, lon3):
    # taken from SimplifyWay.java of JOSM
    # From Aviaton Formulary v1.3 http://williams.best.vwh.net/avform.htm
    distAD = dist(lat1, lon1, lat3, lon3)
    crsAD = course(lat1, lon1, lat3, lon3)
    crsAB = course(lat1, lon1, lat2, lon2)
    return math.asin(math.sin(distAD) * math.sin(crsAD - crsAB))

def dist(lat1, lon1, lat2, lon2):
    # taken from SimplifyWay.java of JOSM
    # From Aviaton Formulary v1.3 http://williams.best.vwh.net/avform.htm
    return 2 * math.asin(math.sqrt(math.pow(math.sin((lat1 - lat2) / 2), 2) + math.cos(lat1) * math.cos(lat2)
                * math.pow(math.sin((lon1 - lon2) / 2), 2)))
def course(lat1, lon1, lat2, lon2):
    # taken from SimplifyWay.java of JOSM
    # From Aviaton Formulary v1.3 http://williams.best.vwh.net/avform.htm
    return math.atan2(math.sin(lon1 - lon2) * math.cos(lat2), math.cos(lat1) * math.sin(lat2) - math.sin(lat1)
                * math.cos(lat2) * math.cos(lon1 - lon2)) \
                % (2 * math.pi)


def isRequiredNode(osm_data, node):
    result = False
    if len(node.tags) > 0:
        result = True
    elif len(node.ways) > 0:
        way = osm_data.ways[list(node.ways)[0]]
        n1,n2 = way.get_previous_and_next_node_id(node.id())
        n1_n2_set = set([n1,n2])
        for way_id in node.ways:
            way = osm_data.ways[way_id]
            if way.nodes[:-1].count(node.id()) > 1:
                result = True
            n1,n2 = way.get_previous_and_next_node_id(node.id())
            if set([n1,n2]) != n1_n2_set:
                result = True
    return result


def split_node_list_at_required_nodes(osm_data, nodes):
    result = [[nodes[0]]]
    for n in nodes[1:]:
        result[-1].append(n)
        if isRequiredNode(osm_data, n):
            result.append([n])
    if (len(result) > 1) and (nodes[0].id() == nodes[-1].id()):
        # The input node list was a closed way, so we concatenate the first and last lists:
        result[-1] = result[-1] + result[0][1:]
        del(result[0])
    return result


def remove_duplicated_nodes_in_ways(osm_data):
    for way in osm_data.ways.values():
        i = 1
        previous = way.nodes[0]
        while i < len(way.nodes):
            if way.nodes[i] == previous:
                del way.nodes[i]
            else:
                previous = way.nodes[i]
                i = i + 1
        if len(way.nodes) <= 3:
            osm_data.delete_way(way)

def copy_tags(src,dst):
    for tag,val in src.tags.iteritems():
        # in case of tag confict keep the longest value
        if (not tag in dst.tags) or (len(dst.tags[tag]) < len(val)):
            if VERBOSE: print "  copy tag ", tag, " => ", val
            dst.tags[tag] = val

def remove_identical_ways(osm_data):
    # We assume that the ways are all closed and reversable
    ways_hashed_by_sorted_node_list = {}
    for way in osm_data.ways.values():
        if way.nodes[0] == way.nodes[-1]:
            nodes_ids = way.nodes[:-1]
            min_id = min(nodes_ids)
            min_index = nodes_ids.index(min_id)
            # rearange starting with smallest one:
            nodes_ids = nodes_ids[min_index:] + nodes_ids[:min_index]
            if len(nodes_ids) > 1:
                if nodes_ids[1] < nodes_ids[-1]:
                    #reverse the order of the nodes except the first one which we keep at the first place:
                    tail = nodes_ids[1:]
                    tail.reverse()
                    nodes_ids = [nodes_ids[0]] + tail
            else:
                if VERBOSE: print "ERROR: way", way.id(), "has only one 1 node ???"
            nodes_ids = tuple(nodes_ids) # to be hashable
        else:
            nodes_ids = tuple(way.nodes) # to be hashable
        if nodes_ids in ways_hashed_by_sorted_node_list:
            keeped_way = ways_hashed_by_sorted_node_list[nodes_ids]
            if VERBOSE: print "suppress way ", way.id(), " keeping identical way ", keeped_way.id()
            copy_tags(way, keeped_way)
            osm_data.replace_way(way, keeped_way)
        else:
            ways_hashed_by_sorted_node_list[nodes_ids] = way


def way_angle_at_node(osm_data, way, node):
    "return the angle the way is doing at this node"
    prv,nxt = way.get_previous_and_next_node(node)
    p0,p1,p2 = [n.position for n in [prv, node, nxt]]
    return p0.minus(p1).angle(p2.minus(p1))


def min_node_angle(osm_data, node):
    """"return the minimum angle ways are doing at this node."""
    return min([math.pi * 2] + [way_angle_at_node(osm_data, osm_data.ways[way_id], node) for way_id in node.ways])


class OsmData(Osm):
    def __init__(self, attrs):
        Osm.__init__(self, attrs)
        self.nodes_rtree = rtree.index.Index()
    def add_bounds(self, bounds_attrs):
        Osm.add_bounds(self, bounds_attrs)
        self.inputTransform, self.outputTransform = get_centered_metric_equirectangular_transformation(self.bbox())
    def add_node(self, node):
        Osm.add_node(self, node)
        self.nodes_rtree.insert(node.id(), (node.position.x, node.position.y), node.id())
    def create_node(self, attrs,tags=None):
        node = NodeData(attrs, tags, self)
        self.add_node(node)
        return node
    def create_node_at_xy(self, coords):
        node = NodeData({"lon":"0","lat":"0"}, {}, self)
        node.position = Point(coords[0], coords[1])
        lon, lat = self.outputTransform.transform_point(node.position)
        if VERBOSE: print "create node ", node.id(), "at ",lon, ",", lat
        node.attrs["lon"] = str(lon)
        node.attrs["lat"] = str(lat)
        self.add_node(node)
        return node
    def create_way(self, attrs, tags=None):
        way = WayData(attrs, tags, self)
        self.add_way(way)
        return way
    def create_relation(self, attrs, tags=None):
        relation = RelationData(attrs, tags, self)
        self.add_relation(relation)
        return relation
    def __delete_from_his_relations__(self, item):
        item_type = item.type()
        for relelation_id in item.relations:
            relelation = self.relations[relelation_id]
            i = 0
            while i < len(relelation.members):
                member = relelation.members[i]
                if (member.get("type") == item_type) and (member.get("ref") == item.attrs["id"]):
                    del(relelation.members[i])
                else:
                  i = i + 1
            if len(relelation.members) == 0:
                self.delete_relation(relation)
    def delete_node(self, node):
        node_id = node.id()
        self.nodes_rtree.delete(node_id, (node.position.x, node.position.y))
        if VERBOSE: print "delete node ", node_id
        for way_id in node.ways:
            if VERBOSE: print "  from way ", way_id
            way = self.ways[way_id]
            if (way.nodes[0] == node_id) and (way.nodes[-1] == node_id):
                del(way.nodes[0])
                way.nodes[-1] = way.nodes[0]
            while node_id in way.nodes:
                way.nodes.remove(node_id)
        self.__delete_from_his_relations__(node)
        del(self.nodes[node_id])
    def delete_way(self, way):
        if VERBOSE: print "delete way", way.id()
        for node_id in way.nodes:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                if way.id() in node.ways:
                    node.ways.remove(way.id())
                if (len(node.ways) == 0) and (len(node.tags) == 0):
                   self.delete_node(node)
        self.__delete_from_his_relations__(way)
        del(self.ways[way.id()])
    def delete_relation(self, relation):
        for item,_ in self.iter_relation_members(relation):
            item.relations.remove(relation.id())
        del(self.relations[relation.id()])
    def search_nodes(self, bbox):
        for result in self.nodes_rtree.intersection(bbox, objects=True):
            node_id = result.object
            yield self.nodes[node_id]
    def __replace_in_relations__(self, src, dst):
        for rel_id in src.relations:
            if VERBOSE: print "   replace in relation ", rel_id
            rel = self.relations[rel_id]
            for member in rel.members:
                if (member.get("type") == src.type()) and (member.get("ref") == str(src.id())):
                    member["ref"] = str(dst.id())
    def replace_node(self, src_node, dst_node):
        src_id = src_node.id()
        dst_id = dst_node.id()
        if VERBOSE: print "replace node ", src_id, " by ", dst_id
        for way_id in list(src_node.ways):
            dst_node.ways.add(way_id) 
            way = self.ways[way_id]
            i = 0
            while i < (len(way.nodes)-1):
                if way.nodes[i] in [src_id, dst_id]:
                    if way.nodes[(i + len(way.nodes)-2) % (len(way.nodes)-1)] in [dst_id, src_id]:
                        del(way.nodes[i])
                    else:
                        way.nodes[i] = dst_id
                        i = i + 1
                else:
                    i = i + 1
            way.nodes[-1] = way.nodes[0]
        src_node.ways.clear()
        copy_tags(src_node, dst_node)
        self.__replace_in_relations__(src_node, dst_node)
        self.delete_node(src_node)
    def replace_way(self, src, dst):
        dst_id = dst.id()
        self.__replace_in_relations__(src, dst)
        copy_tags(src, dst)
        self.delete_way(src)
    def move_node(self, node, new_position):
        self.nodes_rtree.delete(node.id(), (node.position.x, node.position.y))
        node.position = new_position
        lon, lat = self.outputTransform.transform_point(new_position)
        self.attrs["lon"] = str(lon)
        self.attrs["lat"] = str(lat)
        self.nodes_rtree.insert(node.id(), (node.position.x, node.position.y), node.id())


    
class NodeData(Node):
    def __init__(self, attrs, tags, osm_data):
        Node.__init__(self, attrs, tags)
        self.ways = set()
        self.relations = set()
        self.position = osm_data.inputTransform.transform_point(
            (self.lon(), self.lat()))



class WayData(Way):
    def __init__(self, attrs,tags, osm_data):
        Way.__init__(self, attrs, tags)
        self.relations = set()
        self.osm_data = osm_data
    def add_node(self, node):
        if (type(node) == str) or (type(node) == unicode) or (type(node) == int):
            id = int(node)
            node = self.osm_data.nodes[id]
        else:
            id = node.id()
        self.nodes.append(id)
        node.ways.add(self.id())
    def get_previous_and_next_node_id(self, node_id):
        i = self.nodes.index(node_id)
        if self.nodes[0] == self.nodes[-1]:
            size = len(self.nodes)-1
            prv = self.nodes[(i + size - 1) % size]
            nxt = self.nodes[(i + + 1) % size]
        else:
            prv = self.nodes[i-1] if i>0 else None
            nxt = self.nodes[i+1] if i<(len(self.nodes)-1) else None
        return prv,nxt
    def get_previous_and_next_node(self, node):
        prv,nxt = self.get_previous_and_next_node_id(node.id())
        return self.osm_data.nodes[prv] if prv != None else None,\
               self.osm_data.nodes[nxt] if nxt != None else None


class RelationData(Relation):
    def __init__(self, attrs,tags, osm_data):
        Relation.__init__(self, attrs, tags)
        self.relations = set()
        self.osm_data = osm_data
    def add_member_attrs(self, attrs):
        Relation.add_member_attrs(self, attrs)
        item = self.osm_data.get(attrs["type"],int(attrs["ref"]))
        item.relations.add(self.id())

class Timer():
    def __init__(self, msg):
        self.start = timeit.default_timer()
        self.msg = msg
        if VERBOSE:
            print msg
    def __call__(self):
        return timeit.default_timer() - self.start
    def prnt(self):
        if VERBOSE:
            print self.msg + " => " + str(round(self(), 4)) +  " s"


if __name__ == '__main__':
    sys.exit(main(sys.argv))

