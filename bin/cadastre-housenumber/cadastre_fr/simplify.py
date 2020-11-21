#!/usr/bin/env python3
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


import copy
import math
import os.path
import operator
import rtree.index
from shapely.geometry.polygon import Polygon
from functools import reduce

from .osm       import Osm, Node, Way, Relation, OsmParser, OsmWriter
from .tools     import iteritems, itervalues, iterkeys
from .geometry  import Point
from .geometry  import BoundingBox
from .transform import LinearTransform
from .transform import get_centered_metric_equirectangular_transformation_from_osm
from .geometry  import orthoprojection_on_segment_ab_of_point_c
from .globals   import VERBOSE
from .globals   import EARTH_RADIUS_IN_METER
from .globals   import EARTH_CIRCUMFERENCE_IN_METER


def simplify(osm_data, merge_distance, join_distance, simplify_threshold):
  inputTransform, outputTransform = get_centered_metric_equirectangular_transformation_from_osm(osm_data)

  for node in itervalues(osm_data.nodes):
    node.ways = set()

  for way in itervalues(osm_data.ways):
    way.relations = set()
    for node_id in way.nodes:
        node = osm_data.nodes[node_id]
        node.ways.add(way.id())

  for rel in itervalues(osm_data.relations):
     for rtype,rref,rrole in rel.itermembers():
        if rtype == "way":
            osm_data.ways[rref].relations.add(rel.id())

  for node in list(osm_data.nodes.values()):
    node.position = inputTransform.transform_point(
        (node.lon(), node.lat()))

  for node in list(osm_data.nodes.values()):
    node.min_angle = min_node_angle(osm_data, node)

  merge_close_nodes(osm_data, merge_distance, False)

  remove_duplicated_nodes_in_ways(osm_data)

  simplify_ways(osm_data, simplify_threshold)

  join_close_nodes_and_remove_inside_ways(osm_data, join_distance)

  merge_close_nodes(osm_data, simplify_threshold, True)

  suppress_identical_ways(osm_data)

  for n in itervalues(osm_data.nodes):
    lon, lat = outputTransform.transform_point(n.position)
    n.attrs["lon"] = str(lon)
    n.attrs["lat"] = str(lat)


def merge_close_nodes(osm_data, max_distance, can_merge_same_way):
  """Merge nodes that are close to one another while not being members of the same ways.

     We assume nodes are not part of relations
     and that nodes are part of the ways which ids are listed in node's .ways set attribute
     We assume that the ways are closed
  """
  nodes_index = rtree.index.Index()
  for node in list(osm_data.nodes.values()):
      p = node.position
      search_bounds = p.x - max_distance, p.y - max_distance, \
                      p.x + max_distance, p.y + max_distance
      keep = True
      for near_node_id in [e.object for e in nodes_index.intersection(search_bounds, objects=True)]:
          near_node = osm_data.nodes[near_node_id]
          if p.distance(near_node.position) < max_distance:
             if can_merge_nodes(osm_data, node, near_node, can_merge_same_way):
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

def can_merge_nodes(osm_data, n1, n2, can_merge_same_way):
    result = True
    same_ways = n1.ways & n2.ways
    if len(same_ways) > 0:
        if can_merge_same_way:
            for way_id in same_ways:
                way = osm_data.ways[way_id]
                n1_previous, n1_id, n1_following = get_previous_it_and_following_from_closed_list(way.nodes, n1.id())
                if (n2.id() != n1_previous) and (n2.id() != n1_following):
                    result = False
        else:
            result = False
    return result


def join_close_nodes_and_remove_inside_ways(osm_data, join_distance):
    ways_index = rtree.index.Index()
    for way in list(osm_data.ways.values()):
        bbox = BoundingBox.of_points([osm_data.nodes[node_id].position for node_id in way.nodes])
        way.bbox = [bbox.x1,bbox.y1,bbox.x2, bbox.y2]
        ways_index.insert(way.id(), way.bbox, way.id())
    join_close_nodes(osm_data, ways_index, join_distance)
    remove_inside_ways(osm_data, ways_index)


def join_close_nodes(osm_data, ways_index, distance):
    """Join nodes to close ways."""
    for node in list(osm_data.nodes.values()):
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
          if can_join_node_to_way(node, way):
            node = osm_data.nodes[node_id]
            i = 0
            for i in range(len(way.nodes) - 1):
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
          if VERBOSE: print(("Join node  {} to way {}".format(node_id, closest_way.id())))
          closest_way.nodes.insert(closest_index, node_id)
          node.ways.add(closest_way.id())
          node.position = closest_position
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
        n1_previous, _, n1_next = get_previous_it_and_following_from_closed_list(way.nodes, n1.id())
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

def remove_inside_ways(osm_data, ways_index):
    for way1 in list(osm_data.ways.values()):
        if len(way1.relations) == 0:
            polygon1 =  polygon_of_way(osm_data, way1)
            for way2_id in [e.object for e in ways_index.intersection(way1.bbox, objects=True)]:
                way2 = osm_data.ways[way2_id]
                if (way2_id != way1.id()) and (len(way2.relations) == 0) and (("wall" in way1.tags) or ("wall" not in way2.tags)):
                    polygon2 =  polygon_of_way(osm_data, way2)
                    try:
                      if polygon2.contains(polygon1):
                        if VERBOSE: print(("way  {} inside {}".format(way1.id(), way2_id)))
                        ways_index.delete(way1.id(), way1.bbox)
                        delete_way(osm_data, way1)
                        break
                    except:
                        # polygon2.contains(polygon1) will fail if either polygon1 or 2
                        # are invalid, but it is faster to catch exceptions than
                        # to check for .is_valid
                        pass


def polygon_of_way(osm_data, way):
    return Polygon([osm_data.nodes[i].position for i in way.nodes])


def simplify_ways(osm_data, threshold):
    for way in list(osm_data.ways.values()):
        nodes = [osm_data.nodes[node_id] for node_id in way.nodes]
        for node_sublist in split_node_list_at_required_nodes(osm_data, nodes):
            keeped_nodes = buildSimplifiedNodeSet(node_sublist, 0, len(node_sublist)-1, threshold)
            for n in node_sublist:
                if not n in keeped_nodes:
                  delete_node(osm_data, n)
        if len(way.nodes) <= 3:
            delete_way(osm_data, way)


def buildSimplifiedNodeSet(nodes, fromIndex, toIndex, threshold):
    # taken from SimplifyWay.java of JOSM
    result = set() # the set of nodes to keep
    fromN = nodes[fromIndex]
    toN = nodes[toIndex]
    # Get max xte
    imax = -1
    xtemax = 0.0
    for i in range(fromIndex+1, toIndex):
        n = nodes[i]
        xte = abs(EARTH_RADIUS_IN_METER
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


def isRequiredNode(osm_data, node):
    result = False
    if len(node.tags) > 0:
        result = True
    elif len(node.ways) > 0:
        way = osm_data.ways[list(node.ways)[0]]
        n1,_,n2 = get_previous_it_and_following_from_closed_list(way.nodes, node.id())
        n1_n2_set = set([n1,n2])
        for way_id in node.ways:
            way = osm_data.ways[way_id]
            if way.nodes[:-1].count(node.id()) > 1:
                result = True
            n1,_,n2 = get_previous_it_and_following_from_closed_list(way.nodes, node.id())
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
    for way in list(osm_data.ways.values()):
        i = 1
        previous = way.nodes[0]
        while i < len(way.nodes):
            if way.nodes[i] == previous:
                del way.nodes[i]
            else:
                previous = way.nodes[i]
                i = i + 1
        if len(way.nodes) <= 3:
            delete_way(osm_data, way)

def replace_node(osm_data, src_node, dst_node):
  # We assume nodes are not part of relations
  # and that nodes are part of the ways which ids are listed in node's .ways set attribute
  # We assume that the ways are closed
  src_id = src_node.id()
  dst_id = dst_node.id()
  if VERBOSE: print(("replace node {} by {}".format(src_id, dst_id)))
  for way_id in src_node.ways:
    way = osm_data.ways[way_id]
    if dst_id in way.nodes:
      # we just remove src_node from the way
      if (way.nodes[0] == src_id) and (way.nodes[-1] == src_id):
          while src_id in way.nodes:
              way.nodes.remove(src_id)
          way.nodes.append(way.nodes[0])
      else:
          while src_id in way.nodes:
              way.nodes.remove(src_id)
    else:
      dst_node.ways.add(way_id)
      for i in range(len(way.nodes)):
        if way.nodes[i] == src_id:
          way.nodes[i] = dst_id
  copy_tags(src_node, dst_node)
  del(osm_data.nodes[src_id])

def copy_tags(src,dst):
    for tag,val in iteritems(src.tags):
        # in case of tag confict keep the longest value
        if (not tag in dst.tags) or (len(dst.tags[tag]) < len(val)):
            if VERBOSE: print(("  copy tag {} => {}".format(tag, val)))
            dst.tags[tag] = val

def delete_node(osm_data, node):
  # We assume nodes are not part of relations
  # and that nodes are part of the ways which ids are listed in node's .ways set attribute
  # We assume that the ways are closed
  node_id = node.id()
  if VERBOSE: print(("delete node  {}".format(node_id)))
  for way_id in node.ways:
    if VERBOSE: print(("  from way  {}".format(way_id)))
    way = osm_data.ways[way_id]
    if (way.nodes[0] == node_id) and (way.nodes[-1] == node_id):
        del(way.nodes[0])
        way.nodes[-1] = way.nodes[0]
    while node_id in way.nodes:
        way.nodes.remove(node_id)
  del(osm_data.nodes[node_id])

def suppress_identical_ways(osm_data):
    # We assume that the ways are all closed and reversable
    ways_hashed_by_sorted_node_list = {}
    for way in list(osm_data.ways.values()):
        nodes_ids = way.nodes[:-1] # remove the last one that should be the same as first one (closed way)
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
            if VERBOSE: print(("ERROR: way {} has only one 1 node ???".format(way.id())))
        nodes_ids = tuple(nodes_ids) # to be hashable
        if nodes_ids in ways_hashed_by_sorted_node_list:
            keeped_way = ways_hashed_by_sorted_node_list[nodes_ids]
            if VERBOSE: print(("suppress way  {} keeping identical way {}".format(way.id(), keeped_way.id())))
            copy_tags(way, keeped_way)
            # Replace in relations
            for rel_id in way.relations:
                if VERBOSE: print(("   replace in relation  {}".format(rel_id)))
                rel = osm_data.relations[rel_id]
                for member in rel.members:
                    if (member.get("type") == "way") and (member.get("ref") == str(way.id())):
                        member["ref"] = str(keeped_way.id())
            delete_way(osm_data, way)
        else:
            ways_hashed_by_sorted_node_list[nodes_ids] = way

def delete_way(osm_data, way):
    if VERBOSE: print(("delete way {}".format(way.id())))
    del(osm_data.ways[way.id()])
    for node_id in way.nodes:
        if node_id in osm_data.nodes:
          node = osm_data.nodes[node_id]
          if way.id() in node.ways:
              node.ways.remove(way.id())
              if (len(node.ways) == 0) and (len(node.tags) == 0):
                  delete_node(osm_data, node)
    for rel_id in way.relations:
        rel = osm_data.relations[rel_id]
        i = 0
        while i < len(rel.members):
            member = rel.members[i]
            if (member.get("type") == "way") and (member.get("ref") == way.attrs["id"]):
                del(members[i])
            else:
              i = i + 1

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
    #if way.nodes[0] != way.nodes[-1]:
    #    raise Exception("WAY " + way_id + " NON FERME")
    node_id = node.id()
    p0,p1,p2 = [osm_data.nodes[i].position for i in get_previous_it_and_following_from_closed_list(way.nodes, node_id)]
    return p0.minus(p1).angle(p2.minus(p1))


def min_node_angle(osm_data, node):
    """"return the minimum angle ways are doing at this node."""
    return min([math.pi * 2] + [way_angle_at_node(osm_data, osm_data.ways[way_id], node) for way_id in node.ways])

