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



import sys
import copy
import operator
import rtree.index
from shapely.geometry.polygon import Polygon
from shapely.geometry.polygon import LineString


from cadastre_fr.osm        import Osm, Node, Way, Relation, OsmParser, OsmWriter
from cadastre_fr.osm_tools  import osm_add_polygon_or_multipolygon
from cadastre_fr.osm_tools  import osm_add_line_way
from cadastre_fr.parser     import CadastreParser
from cadastre_fr.globals    import SOURCE_TAG
from cadastre_fr.geometry   import SimilarGeometryDetector
from cadastre_fr.transform  import CadastreToOSMTransform
from cadastre_fr.recognizer import BuildingPathRecognizer
from cadastre_fr.recognizer import WaterPathRecognizer
from cadastre_fr.recognizer import StandardPathRecognizer

def pdf_2_osm_buildings_water_and_limit(pdf_filename_list):
    projection, buildings, light_buildings, waters, riverbanks, limit  = \
        pdf_2_buildings_water_and_limit(pdf_filename_list)
    cadastre_to_osm_transform = CadastreToOSMTransform(projection).transform_point
    osm_buildings = buildings_to_osm(buildings, light_buildings, cadastre_to_osm_transform)
    osm_water = water_to_osm(waters, riverbanks, cadastre_to_osm_transform)
    osm_limit = limit_to_osm(limit, cadastre_to_osm_transform)
    return osm_buildings, osm_water, osm_limit

def buildings_to_osm(buildings, light_buildings, transform):
    osm = Osm({})
    all_nodes_set = {}
    similar_polygons_detector = SimilarGeometryDetector()
    def add_building(linear_rings, isLight):
        polygon = Polygon(linear_rings[0], linear_rings[1:])
        if similar_polygons_detector.test_and_add(polygon):
            return
        item = osm_add_polygon_or_multipolygon(osm, polygon, transform, all_nodes_set)
        item.tags["building"] = "yes"
        if isLight:
            tags["wall"] = "no"
        item.tags["source"] = SOURCE_TAG
        if type(item) == Relation:
            for elem, role in osm.iter_relation_members(item):
                elem.tags["source"] = SOURCE_TAG
    for linear_rings in buildings:
        add_building(linear_rings, False)
    for linear_rings in light_buildings:
        add_building(linear_rings, True)
    return osm

def water_to_osm(waters, riverbanks, transform):
    osm = Osm({})
    all_nodes_set = {}
    similar_polygons_detector = SimilarGeometryDetector()
    def add_water(linear_rings, isRiverbank):
        polygon = Polygon(linear_rings[0], linear_rings[1:])
        if similar_polygons_detector.test_and_add(polygon):
            return
        item = osm_add_polygon_or_multipolygon(osm, polygon, transform, all_nodes_set)
        if isRiverbank:
            item.tags["waterway"] = "riverbank"
        else:
            item.tags["natural"] = "water"
        item.tags["source"] = SOURCE_TAG
        if type(item) == Relation:
            for elem, role in osm.iter_relation_members(item):
                elem.tags["source"] = SOURCE_TAG
    for linear_rings in waters:
        add_water(linear_rings, False)
    for linear_rings in riverbanks:
        add_water(linear_rings, True)
    return osm

def limit_to_osm(limit, transform):
    osm = Osm({})
    all_nodes_set = {}
    similar_geometry_detector = SimilarGeometryDetector()
    def add_limit(linear_rings):
        for ring in linear_rings:
            line = LineString(ring)
            if similar_geometry_detector.test_and_add(line):
                return
            item  = osm_add_line_way(osm, line, transform, all_nodes_set)
            item.tags["boundary"] = "administrative"
            item.tags["source"] = SOURCE_TAG
    for linear_rings in limit:
        add_limit(linear_rings)
    return osm

def pdf_2_buildings_water_and_limit(pdfs):
    recognizer = StandardPathRecognizer()
    cadastre_parser = CadastreParser([recognizer.handle_path])
    sys.stdout.write((u"Parse les exports PDF du cadastre:\n").encode("utf-8"))
    sys.stdout.flush()
    nb = [0] * 5
    for filename in pdfs:
        cadastre_parser.parse(filename)
        new_nb = [len(recognizer.buildings), len(recognizer.light_buildings), len(recognizer.waters), len(recognizer.riverbanks), len(recognizer.limit)]
        diff = map(operator.sub, new_nb, nb)
        sys.stdout.write((filename + ": " + ", ".join([
              str(val) + " " + name 
              for name,val in zip([u"buildings", u"light buildings", u"water", u"riverbank", u"limit"], diff)])
            + "\n").encode("utf-8"))
        sys.stdout.flush()
        nb = new_nb
    return cadastre_parser.cadastre_projection, recognizer.buildings, recognizer.light_buildings, recognizer.waters, recognizer.riverbanks, recognizer.limit



