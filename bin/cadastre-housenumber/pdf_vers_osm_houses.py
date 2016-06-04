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
Extrait les buildings depuis des fichier PDF du cadastre,
"""


import re
import sys
import copy
import os.path
import operator
import itertools
import rtree.index

from glob import glob
from shapely.geometry.polygon import Polygon

from osm                            import Osm,Node,Way,Relation,OsmParser,OsmWriter
from pdf_vers_osm_housenumbers      import CadastreParser
from pdf_vers_osm_housenumbers      import CadastreToOSMTransform
from cadastre_vers_osm_adresses     import SOURCE_TAG


TOLERANCE = 0.3
IMG_SIZE = 256


def main(argv):
    if len(argv) == 2 and len(argv[1]) == 5:
        prefix = argv[1]
        pattern = prefix + "-[0-9]*-[0-9]*.pdf"
        pdf_args = glob(pattern)
        osm_args = [prefix + "-houses.osm"]
        other_args = []
    else:
        pdf_args = [f for f in argv[1:] if os.path.splitext(f)[1] == ".pdf"]
        osm_args = [f for f in argv[1:] if os.path.splitext(f)[1] == ".osm"]
        other_args = [f for f in argv[1:] if os.path.splitext(f)[1] not in (".pdf", ".osm")]
        prefix = os.path.commonprefix(pdf_args)
    if len(other_args) != 0:
        print "ERROR: invalid argument ", other_args[0]
        return -1
    elif len(pdf_args) == 0:
        print "ERROR: not enough .pdf arguments"
    elif len(osm_args) > 1:
        print "ERROR: too many .osm arguments"
        return -1
    else:
        cadastre_buildings = pdf_vers_osm_buildings(pdf_args)
        compute_osm_bounds(cadastre_buildings)
        OsmWriter(cadastre_buildings).write_to_file(prefix + "-houses.osm")
    return 0


def bounds_center(bounds):
    minx, miny, maxx, maxy = bounds
    centerx = (minx + maxx) / 2
    centery = (miny + maxy) / 2
    return (centerx, centery)

class SimilarPolygonsDetector(object):
    def __init__(self, precision_decimal=1):
        self.index= rtree.index.Index()
        self.precision = precision_decimal
        self.polygons = []
    def contains(self, polygon):
        center = bounds_center(polygon.bounds)
        for i in self.index.intersection(center):
            if polygon.almost_equals(self.polygons[i], self.precision):
                return True
        return False
    def test_and_add(self, polygon):
        if self.contains(polygon):
            return True
        else:
            i = len(self.polygons)
            self.polygons.append(polygon)
            self.index.insert(i, polygon.bounds)
            return False

def pdf_vers_osm_buildings(pdf_filename_list):
    projection, buildings, light_buildings = \
        pdf_vers_buildings(pdf_filename_list)
    cadastre_to_osm_transform = CadastreToOSMTransform(projection)
    all_nodes = {}
    similar_polygons_detector = SimilarPolygonsDetector()
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
    osm = Osm({'upload':'false'})
    for building in buildings:
        add_building(osm, building, False)
    for building in light_buildings:
        add_building(osm, building, True)
    return osm


def pdf_vers_buildings(pdfs):
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


class BuildingPathRecognizer(object):
    def __init__(self):
        self.commands_re = re.compile("^(MLLLL*Z)+$")
        self.buildings = []
        self.light_buildings = []
    def handle_path(self, path, transform):
        # style="fill:#ffcc33;fill-opacity:1;fill-rule:evenodd;stroke:none"
        # style="fill:#ffe599;fill-opacity:1;fill-rule:evenodd;stroke:none"
        if self.commands_re.match(path.commands) and path.style:
            is_building = path.style.find("fill:#ffcc33") >= 0
            is_light_building = path.style.find("fill:#ffe599;") >= 0
            if is_building or is_light_building:
                points = map(transform, path.points)
                linear_rings = []
                for commands_ring in path.commands[:-1].split('Z'):
                    first = points[0]
                    last = points[len(commands_ring)-1]
                    linear_rings.append(points[:len(commands_ring)])
                    points = points[len(commands_ring):]
                if len(linear_rings) > 0:
                    #print linear_rings
                    if is_light_building:
                        self.light_buildings.append(linear_rings)
                    else:
                        self.buildings.append(linear_rings)
                    ##Polygon(linear_rings[0], linear_rings[1:]))
                    return True
        return False

def compute_osm_bounds(osm_data):
    min_lon = min([n.lon() for n in osm_data.nodes.itervalues()])
    max_lon = max([n.lon() for n in osm_data.nodes.itervalues()])
    min_lat = min([n.lat() for n in osm_data.nodes.itervalues()])
    max_lat = max([n.lat() for n in osm_data.nodes.itervalues()])
    osm_data.set_bbox([min_lon, min_lat, max_lon, max_lat])


if __name__ == '__main__':
    sys.exit(main(sys.argv))

