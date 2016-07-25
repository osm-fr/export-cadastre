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


from cadastre_fr.osm        import Osm, Node, Way, Relation, OsmParser, OsmWriter
from cadastre_fr.parser     import CadastreParser
from cadastre_fr.globals    import SOURCE_TAG
from cadastre_fr.geometry   import SimilarGeometryDetector
from cadastre_fr.transform  import CadastreToOSMTransform
from cadastre_fr.recognizer import BuildingPathRecognizer



def pdf_2_osm_buildings(pdf_filename_list):
    projection, buildings, light_buildings = \
        pdf_2_buildings(pdf_filename_list)
    cadastre_to_osm_transform = CadastreToOSMTransform(projection)
    all_nodes = {}
    similar_polygons_detector = SimilarGeometryDetector()
    def add_building(osm, building, isLight):
        polygon = Polygon(building[0], building[1:])
        if similar_polygons_detector.test_and_add(polygon):
            return
        tags = {"building":"yes", "source":SOURCE_TAG}
        if isLight:
            tags["wall"] = "no"
        #for linear_ring in list(polygon.interiors) + [polygon.exterior]:
        first = True
        for linear_ring in building:
            if len(building) > 1:
                way = Way({},{"source":SOURCE_TAG})
                osm.add_way(way)
                if first:
                    relation = Relation({},copy.deepcopy(tags))
                    relation.tags["type"] = "multipolygon"
                    relation.add_member(way, "outer")
                    osm.add_relation(relation)
                    first = False
                else:
                    relation.add_member(way, "inner")
            else:
                way = Way({}, copy.deepcopy(tags))
                osm.add_way(way)
            for p in linear_ring:
                p = cadastre_to_osm_transform.transform_point(p)
                key = "%.7f %.7f" % (p.x, p.y)
                if key in all_nodes:
                    n = all_nodes[key]
                else:
                    n = Node({'lon':"%.7f" % p.x, 'lat':"%.7f" % p.y})
                    osm.add_node(n)
                    all_nodes[key] = n
                way.add_node(n)
    osm = Osm({})
    for building in buildings:
        add_building(osm, building, False)
    for building in light_buildings:
        add_building(osm, building, True)
    return osm


def pdf_2_buildings(pdfs):
    building_recognizer = BuildingPathRecognizer()
    cadastre_parser = CadastreParser([building_recognizer.handle_path])
    sys.stdout.write((u"Parse les exports PDF du cadastre:\n").encode("utf-8"))
    sys.stdout.flush()
    nb = [0, 0]
    for filename in pdfs:
        cadastre_parser.parse(filename)
        new_nb = [len(building_recognizer.buildings), 
            len(building_recognizer.light_buildings)]
        diff = map(operator.sub, new_nb, nb)
        sys.stdout.write((filename + ": " + ", ".join([
              str(val) + " " + name 
              for name,val in zip([u"buildings", u"light buildings"], diff)])
            + "\n").encode("utf-8"))
        sys.stdout.flush()
        nb = new_nb
    return cadastre_parser.cadastre_projection, building_recognizer.buildings, building_recognizer.light_buildings



