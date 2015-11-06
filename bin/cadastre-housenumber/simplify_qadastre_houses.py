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

"""


import sys
import copy
import math
import os.path
import rtree.index
from shapely.geometry.polygon import Polygon

#sys.path.append("../../cadastre-openstreetmap-fr/")

from osm import Osm, OsmParser, OsmWriter
from pdf_vers_osm_housenumbers import BoundingBox, LinearTransform, Point
from cherche_osm_buildings import orthoprojection_on_segment_ab_of_point_c


MERGE_DISTANCE = 0.2 # 20 cm
JOIN_DISTANCE = 0.2 # 20 cm
SIMPLIFY_THRESHOLD = 0.2
EARTH_RADIUS_IN_METTER = 6371000
EARTH_CIRCUMFERENCE_IN_METTER = 2*math.pi*EARTH_RADIUS_IN_METTER
VERBOSE=False


def main(argv):
  args = argv[1:]
  merge_distance  = MERGE_DISTANCE  
  join_distance = JOIN_DISTANCE 
  simplify_threshold = SIMPLIFY_THRESHOLD 
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
    elif args[i] == "-v":
      VERBOSE=True
      del(args[i])
    else:
      i = i + 1
  if len(args) == 0 or len(args) > 2 or any([arg.startswith("-") for arg in args]):
      print("Simplify -houses.osm file extracted from the cadastre by Qadastre2OSM program")
      print("USAGE: %s [-m merge_distance] [-j join_distance] [-s simplify_threshold] input-houses.osm [output-houses.osm]" % argv[0])
      return -1
  else:
    input_filename = args[0]
    if len(args) > 1:
      output_filename = args[1]
    else:
      name,ext = os.path.splitext(input_filename)
      output_filename = name + "-simplifie" + ext

    osm_data = OsmParser().parse(input_filename)
    simplify(osm_data, merge_distance, join_distance, simplify_threshold)
    OsmWriter(osm_data).write_to_file(output_filename)
    return 0


def simplify(osm_data, merge_distance, join_distance, simplify_threshold):
  inputTransform, outputTransform = get_centered_metric_equirectangular_transformation(osm_data)

  for node in osm_data.nodes.itervalues():
    node.ways = set()

  for way in osm_data.ways.itervalues():
    for node_id in way.nodes:
        node = osm_data.nodes[node_id]
        node.ways.add(way.id())

  for node in osm_data.nodes.values():
    node.position = inputTransform.transform_point(
        (node.lon(), node.lat()))

  for node in osm_data.nodes.values():
    node.min_angle = min_node_angle(osm_data, node)

  merge_close_nodes(osm_data, merge_distance)

  simplify_ways(osm_data, simplify_threshold)
  
  join_close_nodes(osm_data, join_distance)

  for n in osm_data.nodes.itervalues():
    lon, lat = outputTransform.transform_point(n.position)
    n.attrs["lon"] = str(lon)
    n.attrs["lat"] = str(lat)


def get_centered_metric_equirectangular_transformation(osm_data):
  """ return a Transform from OSM data WSG84 lon/lat coordinate system
      to an equirectangular projection centered on the center of the data, 
      with a unit ~ 1 meter at the center
  """
  bbox = BoundingBox(*osm_data.bbox())
  center = bbox.center()
  bb1 = (center.x, center.y, center.x + 360, center.y + 360)
  bb2 = (0, 0, EARTH_CIRCUMFERENCE_IN_METTER*math.cos(center.y), EARTH_CIRCUMFERENCE_IN_METTER)
  inputTransform = LinearTransform(bb1, bb2)
  outputTransform = LinearTransform(bb2, bb1)
  return inputTransform, outputTransform 


def merge_close_nodes(osm_data, max_distance):
  """Merge nodes that are close to one another while not being members of the same ways.

     We assume nodes are not part of relations
     and that nodes are part of the ways which ids are listed in node's .ways set attribute
     We assume that the ways are closed
  """
  nodes_index = rtree.index.Index()
  for node in osm_data.nodes.values():
      p = node.position
      search_bounds = p.x - max_distance, p.y - max_distance, \
                      p.x + max_distance, p.y + max_distance
      keep = True
      for near_node_id in [e.object for e in nodes_index.intersection(search_bounds, objects=True)]:
          near_node = osm_data.nodes[near_node_id]
          if p.distance(near_node.position) < max_distance:
             if (node.ways & near_node.ways) == set():
               # Amongst the two nodes we keep the one which ways are making
               # the smallest (the sharpest) angle.
               # This way we hope to keep the nodes that are the most relevant
               if node.min_angle < near_node.min_angle:
                  nodes_index.delete(near_node.id(), (near_node.position.x, near_node.position.y))
                  replace_node(osm_data, near_node, node)
               else:
                  replace_node(osm_data, node, near_node)
                  keep = False
               break
      if keep:
          nodes_index.insert(node.id(), (node.position.x, node.position.y), node.id())


def join_close_nodes(osm_data, distance):
    """Join nodes to close ways."""
    ways_index = rtree.index.Index()
    index = 0
    for way in osm_data.ways.values():
        bbox = BoundingBox.of_points([osm_data.nodes[node_id].position for node_id in way.nodes])
        ways_index.insert(index, [bbox.x1,bbox.y1,bbox.x2, bbox.y2], way.id())
    for node in osm_data.nodes.values():
        node_id = node.id()
        position = node.position
        search_bounds = position.x-distance, position.y - distance, \
                        position.x + distance, position.y + distance
        closest_way = None
        closest_position = None
        closest_distance = distance
        closest_index = None
        for way_id in [e.object for e in ways_index.intersection(search_bounds, objects=True)]:
          way = osm_data.ways[way_id]
          if not node_id in way.nodes:
            node = osm_data.nodes[node_id]
            i = 0
            for i in xrange(len(way.nodes) - 1):
              p1 = osm_data.nodes[way.nodes[i]].position
              p2 = osm_data.nodes[way.nodes[i+1]].position
              p = orthoprojection_on_segment_ab_of_point_c(p1,p2, node.position)
              if p !=None and node.position.distance(p) < closest_distance:
                closest_distance = node.position.distance(p)
                closest_way = way
                closest_index = i+1
                closest_position = Point(p[0],p[1])
        if closest_way:
          if VERBOSE: print "Join node ", node_id, " to way ", closest_way.id()
          closest_way.nodes.insert(closest_index, node_id)
          node.ways.add(closest_way.id())
          node.position = closest_position


def simplify_ways(osm_data, threshold):
    for way in osm_data.ways.values():
        nodes = [osm_data.nodes[node_id] for node_id in way.nodes]
        for node_sublist in split_node_list_per_way_belonging(nodes):
            keeped_nodes = buildSimplifiedNodeSet(node_sublist, 0, len(node_sublist)-1, threshold)
            for n in node_sublist:
                if not n in keeped_nodes:
                  delete_node(osm_data, n)


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
        result.add(fromN)
        result.add(toN)
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

def split_node_list_per_way_belonging(nodes):
    """ split the list of nodes in sections where all nodes belong the same set of ways"""
    result = [[nodes[0]]]
    previous_ways = nodes[0].ways
    for n in nodes[1:]:
        if (len(n.ways - previous_ways)>0) and (len(previous_ways - n.ways))>0:
            # on this node we have exited ways, and entered new ones, 
            # so we don't add this node to the previous list, we just start a new one 
            result.append([n])
        elif n.ways - previous_ways: 
            # on this node we have entered a new ways, so we add this
            # node at the end of the previous list
            result[-1].append(n)
            # and we start a new one
            result.append([n])
        elif previous_ways - n.ways:
            # on this node we have exited some ways, so the cut
            # is done on the previous node, which we also add to the
            # new list we start:
            result.append([result[-1][-1], n])
        else:
            # We are still on the same set of ways, we continue the list:
            result[-1].append(n)
        previous_ways = n.ways
    if len(result) > 1 and nodes[0].id() == nodes[-1].id():
        # The input way was a closed way, so we concatenate the first and last lists:
        result[-1] = result[-1] + result[0][1:]
        del(result[0])
    return result 



def replace_node(osm_data, src_node, dst_node):
  # We assume nodes are not part of relations
  # and that nodes are part of the ways which ids are listed in node's .ways set attribute
  # We assume that the ways are closed
  src_id = src_node.id()
  dst_id = dst_node.id()
  if VERBOSE: print "replace node ", src_id, " by ", dst_id
  for way_id in src_node.ways:
    way = osm_data.ways[way_id]
    if dst_id in way.nodes:
      # we just remove src_node from the way
      if (way.nodes[0] == src_id) and (way.nodes[-1] == src_id):
          del(way.nodes[0])
          way.nodes[-1] = way.nodes[0]
      else:
          way.nodes.remove(src_id)
    else:
      dst_node.ways.add(way_id)
      for i in xrange(len(way.nodes)):
        if way.nodes[i] == src_id:
          way.nodes[i] = dst_id
  del(osm_data.nodes[src_id])


def delete_node(osm_data, node):
  # We assume nodes are not part of relations
  # and that nodes are part of the ways which ids are listed in node's .ways set attribute
  # We assume that the ways are closed
  node_id = node.id()
  if VERBOSE: print "delete node ", node_id
  for way_id in node.ways:
    if VERBOSE: print "  from way ", way_id 
    way = osm_data.ways[way_id]
    if (way.nodes[0] == node_id) and (way.nodes[-1] == node_id):
        del(way.nodes[0])
        way.nodes[-1] = way.nodes[0]
    else:
        way.nodes.remove(node_id)
  del(osm_data.nodes[node_id])


def get_previous_it_and_following_from_closed_list(from_list, searching):
    """A closed list is a list from which the last element is ignored as 
       it should be the same as the first one, like list of nodes for a closed way"""
    len_minus_1 = len(from_list) - 1
    i = from_list.index(searching)
    previous = from_list[(i - 1) % len_minus_1]
    following = from_list[(i + 1) % len_minus_1]
    return previous, searching, following
   

def way_angle_at_node(osm_data, way, node):
    "return the angle the way is doing at this node"
    node_id = node.id()
    if way.nodes[0] != way.nodes[-1]:
        if VERBOSE: print "WAY ", way_id, + "NON FERME"
        sys.exit(-1)
    p0,p1,p2 = [osm_data.nodes[i].position for i in get_previous_it_and_following_from_closed_list(way.nodes, node_id)]
    return p0.minus(p1).angle(p2.minus(p1))
    raise KeyError("node " + str(node_id) + " not part of way " + str(way.id()))


def min_node_angle(osm_data, node):
    """"return the minimum angle ways are doing at this node."""
    return min([math.pi * 2] + [way_angle_at_node(osm_data, osm_data.ways[way_id], node) for way_id in node.ways])


sys.exit(main(sys.argv))


