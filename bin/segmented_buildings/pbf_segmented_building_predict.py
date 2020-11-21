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
Parse a .osm.pbf file given as argument,
predict building that may be segmented by the cadastre,
print them
"""


import sys
import os.path

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "cadastre-housenumber"))

import gc
import re
import json
import time
import array
import pickle
import datetime
import argparse
import multiprocessing as mp
import multiprocessing.dummy
from collections import namedtuple
from osgeo import osr    # apt-get install python-gdal
from imposm.parser import OSMParser
import imposm.parser.simple
if __name__ == '__main__':
    if (sys.version_info >= (3, 4)) and hasattr(imposm.parser.simple, 'process_parse'):
        # using forkserver make a huge gain in memory usage
        # due to process created by imposm.parser
        # but this require using a modified version
        # of imposm.parser:
        # https://github.com/tyndare/imposm-parser/commit/0bc32ce2842fc09dd4caa60fafa037a48a551582
        mp.set_start_method('forkserver')

from cadastre_fr.globals    import VERBOSE
from cadastre_fr_segmented  import get_classifier_vector_from_coords
from cadastre_fr.segmented  import load_classifier_and_scaler
from cadastre_fr.segmented  import SEGMENTED_DATA_DIR
from cadastre_fr.tools      import get_git_describe




VERBOSE = True

WayInfo  = namedtuple('WayInfo', ['wall', 'refs'])
NodeInfo = namedtuple('NodeInfo', ['lon', 'lat', 'ways'])

class OSMBuildingsParser(object):
    """Simple parser to get all the ways corresponding to buildings."""
    def __init__(self, concurrency=None):
        self.concurrency = concurrency
        self.nodes = {}
        self.ways = {}
        self.count = 0

    def handle_relations(self, relations):
        # the set tag filter ensure that we are handling a multipolygon building relation
        for rel_id, tags, members in relations:
            for m_id, m_type, m_role in members:
                if m_type == 'way':
                    self.multipolygon_ways_ids.add(m_id)

    def handle_ways(self, ways):
        for way_id, tags, refs in ways:
            if (('building' in tags) or (way_id in self.multipolygon_ways_ids)) \
                        and ((tags.get("source") or "").find("cadastre") >= 0):
                #        and True:
                self.count += 1
                wall = not (tags.get("wall") == "no")
                refs = array.array('l', refs) # save some memory but slower in python2
                self.ways[way_id] = WayInfo(wall, refs)
                this_way_singleton = (way_id,) # tuple faster and more memory efficient than list
                # update for each node the list of connected ways:
                for ref in refs:
                    node_way_list = self.nodes.get(ref)
                    if node_way_list is None:
                        self.nodes[ref] = this_way_singleton
                    else:
                        if way_id not in node_way_list:
                            self.nodes[ref] = node_way_list + this_way_singleton

    def cleanup_before_coords(self):
        """called after ways parsing, and before coords parsing."""
        del self.multipolygon_ways_ids
        gc.collect() # hopping to use less memory in following forked imposm.parser processes

    def handle_coords(self, coords):
        for osmid, lon, lat in coords:
            if osmid in self.nodes:
                way_list = self.nodes[osmid]
                self.nodes[osmid] = NodeInfo(lon, lat, way_list)

    def parse(self, filename):
        self.multipolygon_ways_ids = set()
        if VERBOSE: sys.stderr.write("parse relations\n")
        p1 = OSMParser(
            concurrency = self.concurrency,
            relations_callback = self.handle_relations,
            relations_tag_filter = multipolygon_building_tag_filter)
        p1.parse(filename)
        if VERBOSE: sys.stderr.write("parse ways\n")
        p2 = OSMParser(
            concurrency = self.concurrency,
            ways_callback = self.handle_ways)
        p2.parse(filename)
        if VERBOSE: sys.stderr.write("cleanup\n")
        self.cleanup_before_coords()
        if VERBOSE: sys.stderr.write("parse coords\n")
        p3 = OSMParser(
            concurrency = self.concurrency,
            coords_callback = self.handle_coords)
        p3.parse(filename)


ExtWayInfo  = namedtuple('ExtWayInfo', ['wall', 'refs', 'touching_ways'])
SimpleNodeInfo = namedtuple('SimpleNodeInfo', ['lon', 'lat', 'nb_ways'])


class OSMTouchingBuildingsParser(OSMBuildingsParser):
    """OSM Building Parser that only keep buildings ways that are
       touching others with the same value for the flag 'wall'
    """
    def cleanup_before_coords(self):
        """called after ways parsing, and before coords parsing."""
        if VERBOSE:
            nb_ways = len(self.ways)
            nb_nodes = len(self.nodes)
        ways_ids = list(self.ways.keys())
        if (sys.version_info > (3, 0)):
            ways_ids = tuple(ways_ids)
        for way_id in ways_ids:
            way = self.ways[way_id]
            touching_ways = set()
            for node_id in way.refs:
                touching_ways.update(self.nodes[node_id])
            touching_ways.remove(way_id)
            for touching_way_id in tuple(touching_ways):
                touching_way = self.ways[touching_way_id]
                if touching_way.wall != way.wall:
                    touching_ways.remove(touching_way_id)
            if len(touching_ways) > 0:
                self.ways[way_id] = ExtWayInfo(way.wall, way.refs, tuple(touching_ways))
            else:
                # this is a lonely way, so it can't be segmented, we delete
                del self.ways[way_id]
                # delete its nodes too:
                for ref in way.refs:
                    node_ways = self.nodes.get(ref)
                    if node_ways is not None and way_id in node_ways:
                        if len(node_ways) == 1:
                            del self.nodes[ref]
                        else:
                            i = node_ways.index(way_id)
                            self.nodes[ref] = node_ways[:i] + node_ways[i+1:]
        # Recreate the nodes hashtable for only the nodes we really need the coordinates:
        # (this will free a lot of memory as we have deleted many nodes entry in the hashtable)
        self.nodes = {node_id:len(self.nodes[node_id]) for node_id in self.nodes}
        if VERBOSE:
            sys.stderr.write("{} ways => {}\n".format(nb_ways, len(self.ways)))
            sys.stderr.write("{} nodes => {}\n".format(nb_nodes, len(self.nodes)))
        OSMBuildingsParser.cleanup_before_coords(self)

    def handle_coords(self, coords):
        # Only keep lon,lat, and nb ways
        for node_id, lon, lat in coords:
            if node_id in self.nodes:
                nb_ways = self.nodes[node_id]
                self.nodes[node_id] = SimpleNodeInfo(lon,lat, nb_ways)


def multipolygon_building_tag_filter(tags):
    if not (('building' in tags) and tags.get("type") == "multipolygon"):
        tags.clear()


def get_transform_from_osm_to(projection):
    if  projection is not None:
        source = osr.SpatialReference();
        target = osr.SpatialReference();
        source.ImportFromEPSG(4326);
        target.ImportFromEPSG(projection);
        return osr.CoordinateTransformation(source, target)
    else:
        return None


SegmentedCase = namedtuple('SegmentedCase', ['id1', 'coords1', 'id2', 'coords2'])


class SegmentedBuildingsPredictor(object):
    def __init__(self, concurrency=mp.cpu_count(), projection=2154, chunksize=100, printer=None):
        self.concurrency = concurrency
        self.projection=projection
        self.chunksize = chunksize
        self.printer = printer;
        self.classifier, self.scaler = load_classifier_and_scaler()
        if (sys.version_info > (3, 4)):
            self.mp_context = mp.get_context('fork')
            # 'fork' is significantly faster than 'forkserver' or 'spawn'
            # it could use more memory but we avoid this by
            # creating the processes at the begining
        else:
            self.mp_context = multiprocessing
        self.queue = self.mp_context.Queue(concurrency * 2)
        self.start_processes()

    def predict(self, buildings):
        if VERBOSE: sys.stderr.write("predict\n")
        #self.start_processes()
        segmented_cases = []
        for way_id, way in list(buildings.ways.items()):
            coords = [buildings.nodes[i] for i in way.refs]
            for touching_way_id in way.touching_ways:
                if touching_way_id > way_id: # avoid considering the symetric case a second times
                    touching_way = buildings.ways[touching_way_id]
                    touching_way_coords = [buildings.nodes[i] for i in touching_way.refs]
                    segmented_cases.append(SegmentedCase(
                        way_id, coords, touching_way_id, touching_way_coords))
                    if len(segmented_cases) >= self.chunksize:
                        self.queue.put(segmented_cases)
                        segmented_cases = []
        self.queue.put(segmented_cases)
        self.close()

    def start_processes(self):
        self.processes = []
        for i in range(self.concurrency):
            p = self.mp_context.Process(
                    target=process_prediction,
                    args=(self.scaler, self.classifier, self.projection, self.queue, self.printer))
            p.start()
            self.processes.append(p)

    def close(self, untransform = None):
        for p in self.processes:
            self.queue.put(None)
        for p in self.processes:
            p.join()
        if self.mp_context != multiprocessing.dummy:
            self.queue.close()


def barycentre(coords):
    return tuple(map(mean, list(zip(*coords))))


def common_coords_barycentre(coords1, coords2):
    """return the barycentre of the coords that are both member
       of the list coords1 and coords2"""
    common_coords = set(coords1) and set(coords2)
    return barycentre(common_coords)


def bbox(coords1):
    xs, ys, _ = list(zip(*coords))
    return min(xs), min(ys), max(xs), max(y)


def process_prediction(scaler, classifier, projection, queue, printer):
    transform = get_transform_from_osm_to(projection)
    while True:
        segmented_cases = queue.get()
        if segmented_cases is None:
            break
        for case in segmented_cases:
            coords1 = transform.TransformPoints(case.coords1)
            coords2 = transform.TransformPoints(case.coords2)
            if predict_segmented(scaler, classifier, coords1, coords2):
                printer(case)


class ResultPrinter():
    """Print a SegmentedCase result"""
    def __init__(self, output=None):
        # Use unbuffered output to avoid multiprocessing mixup output
        self.output = output if output!=None else os.fdopen(sys.stdout.fileno(), 'wb', 0)

    def print_header(self):
        pass
    def __call__(self, case):
        self.output.write((json.dumps(
            [{'id': case.id1, 'latlngs':[(c.lat, c.lon) for c in case.coords1]},
             {'id': case.id2, 'latlngs':[(c.lat, c.lon) for c in case.coords2]}]) + "\n").encode("utf-8"))
    def print_footer(self):
        pass

class OsmosePrinter(ResultPrinter):
    """Print a SegmentedCase result"""
    def print_header(self):
        self.output.write(("""<?xml version="1.0" encoding="UTF-8"?>
    <analysers timestamp="{0}">
    <analyser timestamp="{0}" version="{1}">
    <class item="1" tag="building,geom,fix:chair" id="7" level="3">
    <classtext lang="fr" title="Bâtiment fractionné par le Cadastre ? (estimation)" />
    <classtext lang="en" title="Building segmented by the Cadastre ? (estimate)" />
    </class>\n""".format(datetime.datetime.now().isoformat(), get_git_describe())).encode("utf-8"))


    def __call__(self,case):
        lon,lat,_ = common_coords_barycentre(case.coords1, case.coords2)
        self.output.write(("""<error class="7">
    <location lat="{}" lon="{}" />
    <way id="{}" />
    <way id="{}" />
    </error>\n""".format(lat, lon, case.id1, case.id2)).encode("utf-8"))


    def print_footer(self):
        self.output.write("</analyser>\n</analysers>\n".encode("utf-8"))


def predict_segmented(scaler, classifier, coords1, coords2):
        vector1 = get_classifier_vector_from_coords(coords1, coords2)
        vector2 = get_classifier_vector_from_coords(coords2, coords1)
        if vector1 is not None:
            vector1 = [vector1]
            if scaler is not None:
                vector1 = scaler.transform(vector1)
        if vector2 is not None:
            vector2 = [vector2]
            if scaler is not None:
                vector2 = scaler.transform(vector2)
        return ((vector1 is not None) and classifier.predict(vector1) == [1]) or \
           ((vector2 is not None) and classifier.predict(vector2) == [1])


if (sys.version_info > (3, 4)):
    import statistics
    mean = statistics.mean
else:
    def mean(values):
        return float(sum(values)) / len(values)


def main(args):
    parser = argparse.ArgumentParser(description='Predict segmented buildings in .osm.pbf file.')
    parser.add_argument("--osmose", help="Generate Osmose xml file instead of plain text", action='store_true')
    parser.add_argument("pbf", help=".osm.pbf file to parse", type=str)
    parser.add_argument("projection", nargs="?", help="The projection to use when analysing geomerty", default=2154, type=int)
    args = parser.parse_args(args)

    os.system("cd " + SEGMENTED_DATA_DIR  +"; make -s 3")

    printer = OsmosePrinter() if args.osmose else ResultPrinter()
    printer.print_header()
    predictor = SegmentedBuildingsPredictor(projection=args.projection, printer=printer)
    buildings = OSMTouchingBuildingsParser()
    buildings.parse(args.pbf)
    predictor.predict(buildings)
    printer.print_footer()

if __name__ == '__main__':
    main(sys.argv[1:])


