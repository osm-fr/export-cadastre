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


import math
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry.polygon import Polygon
from shapely.geometry.multipolygon import MultiPolygon


from cadastre_fr.osm        import Osm,Node,Way,OsmWriter,Relation
from cadastre_fr.geometry   import Point
from cadastre_fr.geometry import  angle_projection_on_segment_ab_of_point_c
from cadastre_fr.geometry import orthoprojection_on_segment_ab_of_point_c



def osm_add_point(osm, point, transform):
    if type(point) == ShapelyPoint:
      point = point.coords[0]
    lon,lat = transform(point)
    n = Node({'lon':str(lon),'lat':str(lat)})
    n.position = point # concerve les coordonées du point dans la projection originale, pas très propre...
    osm.add_node(n)
    return n

def osm_add_nodes_way(osm, nodes):
    way = Way({})
    osm.add_way(way)
    for node in nodes:
        way.add_node(node)
    return way
    
def osm_add_line_way(osm, line, transform):
    way = Way({})
    osm.add_way(way)
    for point in line.coords:
        way.add_node(osm_add_point(osm, point, transform))
    return way

def osm_add_polygon(osm, polygon, transform):
    assert(type(polygon) == Polygon)
    for ring in polygon.interiors:
        osm_add_line_way(osm, ring, transform)
    way = osm_add_line_way(osm, polygon.exterior, transform)
    return way

def osm_add_multipolygon(osm, polygon, transform):
    if type(polygon) == Polygon:
        geoms = [polygon]
    elif type(polygon) == MultiPolygon:
        geoms = polygon.geoms
    else:
        print_flush("ERROR: unknown polygon type: " + str(type(polygon)))
    #if len(geoms) == 1 and len(geoms[0].interiors) == 0:
    #    return osm_add_polygon(osm, polygon, transform)
    #else:
    r = Relation({})
    osm.add_relation(r)
    r.tags["type"] = "multipolygon"
    for g in geoms:
        way = osm_add_line_way(osm, g.exterior, transform)
        r.add_member(way, "outer")
        for ring in g.interiors:
            way = osm_add_line_way(osm, ring, transform)
            r.add_member(way, "inner")
    return r
     

def osm_add_way_direction(osm, node, position, angle, taille, transform):
    """ Ajoute un chemin (way) pour indiquer la direction associé a un noeud)"""
    pos1 = (position[0] - taille * math.cos(angle), 
            position[1] - taille * math.sin(angle))
    #pos2 = (position[0] + taille * math.cos(angle), 
    #        position[1] + taille * math.sin(angle))
    p1 = osm_add_point(osm, pos1, transform)
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
        for i in xrange(len(way.nodes)-1):
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

