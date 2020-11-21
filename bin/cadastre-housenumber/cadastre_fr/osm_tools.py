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


import math
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry.polygon import Polygon
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.collection import GeometryCollection
from shapely.geometry.linestring import LineString


from .osm      import Osm,Node,Way,OsmWriter,Relation
from .tools    import print_flush
from .geometry import Point
from .geometry import angle_projection_on_segment_ab_of_point_c
from .geometry import orthoprojection_on_segment_ab_of_point_c



def osm_add_point(osm, point, transform, same_nodes_set = None):
    if type(point) == ShapelyPoint:
        point = point.coords[0]
    lon,lat = transform(point)
    lon,lat = "%.7f" % lon, "%.7f" % lat
    key = lon + "," + lat
    if same_nodes_set != None and key in same_nodes_set:
        return same_nodes_set[key]
    else:
        n = Node({'lon':lon,'lat':lat})
        n.position = point # concerve les coordonées du point dans la projection originale, pas très propre...
        osm.add_node(n)
        if same_nodes_set != None:
            same_nodes_set[key] = n
        return n

def osm_add_nodes_way(osm, nodes):
    way = Way({})
    osm.add_way(way)
    for node in nodes:
        way.add_node(node)
    return way

def osm_add_line_way(osm, line, transform, same_nodes_set = None):
    way = Way({})
    osm.add_way(way)
    for point in line.coords:
        way.add_node(osm_add_point(osm, point, transform, same_nodes_set))
    return way

def osm_add_polygon(osm, polygon, transform, same_nodes_set = None):
    assert(type(polygon) == Polygon)
    for ring in polygon.interiors:
        osm_add_line_way(osm, ring, transform, same_nodes_set)
    way = osm_add_line_way(osm, polygon.exterior, transform, same_nodes_set)
    return way

def osm_add_polygon_or_multipolygon(osm, polygon, transform, same_nodes_set = None):
    if (type(polygon) == MultiPolygon) or (len(polygon.interiors) > 0):
        return osm_add_multipolygon(osm, polygon, transform, same_nodes_set)
    else:
        return osm_add_polygon(osm, polygon, transform, same_nodes_set)

def osm_add_multipolygon(osm, polygon, transform, same_nodes_set = None):
    if type(polygon) == Polygon:
        geoms = [polygon]
    elif type(polygon) == MultiPolygon:
        geoms = polygon.geoms
    elif type(polygon) == GeometryCollection:
        # Cas rencontré sur la commune de Prudemanche (département 28)
        geoms = polygon.geoms
    else:
        print_flush("ERROR: unknown polygon type: " + str(type(polygon)))
        #import pdb;pdb.set_trace()
    #if len(geoms) == 1 and len(geoms[0].interiors) == 0:
    #    return osm_add_polygon(osm, polygon, transform)
    #else:
    r = Relation({})
    osm.add_relation(r)
    r.tags["type"] = "multipolygon"
    for g in geoms:
        if hasattr(g, "exterior"):
            line = g.exterior
        else:
            # In case type(polygon) == GeometryCollection, some
            # geometry may not be polygons, but LineString
            line = g
        way = osm_add_line_way(osm, line, transform, same_nodes_set)
        r.add_member(way, "outer")
        if hasattr(g, "interiors"):
            for ring in g.interiors:
                way = osm_add_line_way(osm, ring, transform, same_nodes_set)
                r.add_member(way, "inner")
    return r


def osm_add_way_direction(osm, node, position, angle, taille, transform, same_nodes_set = None):
    """ Ajoute un chemin (way) pour indiquer la direction associé a un noeud)"""
    pos1 = (position[0] - taille * math.cos(angle),
            position[1] - taille * math.sin(angle))
    #pos2 = (position[0] + taille * math.cos(angle),
    #        position[1] + taille * math.sin(angle))
    p1 = osm_add_point(osm, pos1, transform, same_nodes_set)
    #p2 = osm_add_point(osm, pos2, transform)
    #return osm_add_nodes_way(osm, [p1, node, p2])
    return osm_add_nodes_way(osm, [p1, node])


def nearest_intersection(node, ways, osm, angle = None):
    """Recherche l'intersection la plus proche entre le node et les ways donnés.
       Retourne un tuple (way, index, position) correspondant au way le plus proche,
       à l'index ou inserer le points d'entersection dans la liste des noeuds du way,
       et la position de cette intersection.
       Si l'angle est précisé, la distance sera calculée suivant cet angle,
       sinon une projection orthogonale vers le way sera effectuée.
    """
    best_square_distance = float("inf")
    best_way = None
    best_index = -1
    best_pos = (0,0)
    x,y = node.position
    for way in ways:
        for i in range(len(way.nodes)-1):
            a = osm.nodes[way.nodes[i]]
            b = osm.nodes[way.nodes[i+1]]
            if angle != None:
                p = angle_projection_on_segment_ab_of_point_c(a.position, b.position, node.position, angle)
            else:
                p = orthoprojection_on_segment_ab_of_point_c(a.position, b.position, node.position)
            if p:
                px,py = p
                square_distance = (px-x)*(px-x) + (py-y)*(py-y)
                if square_distance < best_square_distance:
                    best_square_distance = square_distance
                    best_way = way
                    best_index = i+1
                    best_pos = p
    return best_way, best_index, best_pos

