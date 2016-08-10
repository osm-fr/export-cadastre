#!/usr/bin/env python3

import sys
import os.path

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import gc
import re
import time
import array
import pickle
import datetime
import multiprocessing as mp
import multiprocessing.dummy
from collections import namedtuple
from osgeo import osr    # apt-get install python-gdal
from imposm.parser import OSMParser
if (sys.version_info > (3, 0)):
    from urllib.request import urlopen
else:
    from urllib2 import urlopen
import imposm.parser.simple
if __name__ == '__main__':
    if (sys.version_info > (3, 4)) and hasattr(imposm.parser.simple, 'process_parse'):
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

    def cleanup(self):
        del self.multipolygon_ways_ids
        gc.collect()

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
        self.cleanup()
        if VERBOSE: sys.stderr.write("parse nodes\n")
        p3 = OSMParser(
            concurrency = self.concurrency, 
            coords_callback = self.handle_coords)
        p3.parse(filename)


ExtWayInfo  = namedtuple('ExtWayInfo', ['wall', 'refs', 'touching_ways'])


class OSMTouchingBuildingsParser(OSMBuildingsParser):
    """OSM Building Parser that only keep buildings ways that are
       touching others with the same value for the flag 'wall'
    """
    def cleanup(self):
        if VERBOSE:
            nb_ways = len(self.ways)
            nb_nodes = len(self.nodes)
        ways_ids = self.ways.keys()
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
        self.nodes = {node_id:None for node_id in self.nodes}
        if VERBOSE:
            sys.stderr.write("{} ways => {}\n".format(nb_ways, len(self.ways)))
            sys.stderr.write("{} nodes => {}\n".format(nb_nodes, len(self.nodes)))
        OSMBuildingsParser.cleanup(self)

    def handle_coords(self, coords):
        # Only keep lon,lat
        for node_id, lon, lat in coords:
            if node_id in self.nodes:
                self.nodes[node_id] = (lon,lat)


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
    def __init__(self, concurrency=mp.cpu_count(), projection=2154, chunksize=100):
        self.concurrency = concurrency
        self.projection=projection
        self.chunksize = chunksize
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
        for way_id, way in buildings.ways.items():
            coords = [buildings.nodes[i] for i in way.refs]
            for touching_way_id in way.touching_ways:
                if touching_way_id > way_id:
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
                    args=(self.scaler, self.classifier, self.projection, self.queue))
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
    return tuple(map(mean, zip(*coords)))


def common_coords_barycentre(coords1, coords2):
    """return the barycentre of the coords that are both member 
       of the list coords1 and coords2"""
    common_coords = set(coords1) and set(coords2)
    return barycentre(common_coords)


def bbox(coords1):
    x, y = zip(*coords)
    return min(x), min(y), max(x), max(y)


def process_prediction(scaler, classifier, projection, queue):
    transform = get_transform_from_osm_to(projection)
    while True:
        segmented_cases = queue.get()
        if segmented_cases is None:
            break
        for case in segmented_cases:
            coords1 = transform.TransformPoints(case.coords1)
            coords2 = transform.TransformPoints(case.coords2)
            if predict_segmented(scaler, classifier, coords1, coords2):
                output_error_case(case)

def output_header():
    print("""<?xml version="1.0" encoding="UTF-8"?>
<analysers timestamp="{0}">
<analyser timestamp="{0}" version="">
<class item="0" tag="building,geom,fix:chair" id="7" level="3">
<classtext lang="fr" title="Bâtiment fractionné ? par le Cadastre" />
<classtext lang="en" title="Building segmented ? by the Cadastre" />
</class>""".format(datetime.datetime.now().isoformat()))


def output_error_case(case):
    lon,lat = common_coords_barycentre(case.coords1, case.coords2)
    print("""<error class="7">
<location lat="{}" lon="{}" />
<way id="{}" />
<way id="{}" />
</error>""".format(lat, lon, case.id1, case.id2))


def output_footer():
    print("</analyser>")
    print("</analysers>")


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
    os.system("cd " + SEGMENTED_DATA_DIR  +"; make -s 3")
    filename = args[0]
    if len(args) > 1:
        projection = int(args[1])
    else:
        projection = 2154
    output_header()
    predictor = SegmentedBuildingsPredictor(projection=projection)
    buildings = OSMTouchingBuildingsParser()
    buildings.parse(filename)
    predictor.predict(buildings)
    output_footer()


if __name__ == '__main__':
    main(sys.argv[1:])


