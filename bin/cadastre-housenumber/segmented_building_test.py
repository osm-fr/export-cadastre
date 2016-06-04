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
Prends en entrée des fichier osm contenant des building avec
un tag "segmented" contenant des valeurs égales pour les buildings à fusionner,
ou rien ou "segmented"="no" pour ceux à ne pas fusioner,
et "segmented"="?" pour ceux pour lequel c'est ambigue.

De tels fichiers d'entrée peuvent être générés par le programme 
segmented_building_find_joined.py

Ensuite, analyse chaque couple de bâtiment contigues,
utilise le classifier pour dérdire si ils sont fractionnés ou non,
et compare la prédiction avec l'indication présente dans le tag "segmented".

Compte le nombre de cas ok, raté ou de faux positifs.
"""


import re
import sys
import copy
import math
import numpy
import pickle
import os.path
import zipfile
import operator
import itertools
from sklearn import svm

from osm                            import Osm,Node,Way,Relation,OsmParser,OsmWriter
from simplify_qadastre_houses       import get_centered_metric_equirectangular_transformation
from segmented_building_find_joined import compute_transformed_position_and_annotate
from fr_cadastre_segmented          import get_classifier_vector
from segmented_building_train       import open_zip_and_files_with_extension
from segmented_building_train       import get_segmented_analysis_vector_from_osm
from segmented_building_predict     import get_classifier_and_scaler
from segmented_building_predict     import get_buildings_ways
from segmented_building_predict     import iter_contigous_ways
from segmented_building_predict     import predict_segmented


#IMG_SIZE = 256

VERBOSE=True

def main(argv):
    global VERBOSE
    osm_args = [f for f in argv[1:] if os.path.splitext(f)[1] in (".zip", ".osm")]
    other_args = [f for f in argv[1:] if os.path.splitext(f)[1] not in (".zip", ".osm")]
    if len(other_args) != 0:
        return print_usage("invalid argument: " + other_args[0])
    if len(osm_args) == 0:
        return print_usage("not enough file.osm args")

    classifier, scaler = get_classifier_and_scaler()

    score = 0

    for name, stream in open_zip_and_files_with_extension(osm_args, ".osm"):
        if VERBOSE: print "load " + name
        input_osm = OsmParser().parse_stream(stream)
        inputTransform, outputTransform = get_centered_metric_equirectangular_transformation(input_osm)
        compute_transformed_position_and_annotate(input_osm, inputTransform)

        nb_ok, nb_missed, nb_false, missed_osm, false_osm = test_classifier(classifier, scaler, input_osm)

        if VERBOSE: print nb_ok, "correctly found"

        if len(missed_osm.ways) or nb_missed:
            missed_name = os.path.splitext(name)[0] + "-missed.osm"
            if VERBOSE: print nb_missed, " missed detections, write file", missed_name
            OsmWriter(missed_osm).write_to_file(missed_name)
        if len(false_osm.ways) or nb_false:
            false_name = os.path.splitext(name)[0] + "-false.osm"
            if VERBOSE: print nb_false, " false positives, write file", false_name
            OsmWriter(false_osm).write_to_file(false_name)
        score  += nb_ok * 2 - nb_missed - nb_false*10

    if VERBOSE: print "TOTAL SCORE (ok*3 - missed - false*10):"
    print score
    return 0


def test_classifier(classifier, scaler, osm_data):
    false_osm = Osm({'upload':'false'})
    missed_osm = Osm({'upload':'false'})
    nb_ok = 0
    nb_false = 0
    nb_missed = 0
    for building in get_buildings_ways(osm_data):
        for way in iter_contigous_ways(osm_data, building):
            if way.isBuilding and way.hasWall == building.hasWall and way.id() > building.id():
                areSegmented = building.isSegmented and (building.tags.get("segmented") == way.tags.get("segmented"))
                incertain = (building.tags.get("segmented") == "?") or (way.tags.get("segmented") == "?")
                if predict_segmented(classifier, scaler, osm_data, building, way):
                    if areSegmented:
                        nb_ok = nb_ok + 1
                    elif not incertain:
                        nb_false = nb_false + 1
                        add_way_to_other_osm(osm_data, building, false_osm) 
                        add_way_to_other_osm(osm_data, way, false_osm) 
                else:
                    if areSegmented:
                        nb_missed = nb_missed + 1
                        add_way_to_other_osm(osm_data, building, missed_osm) 
                        add_way_to_other_osm(osm_data, way, missed_osm) 
    return nb_ok, nb_missed, nb_false, missed_osm, false_osm


def add_way_to_other_osm(source_osm, way, other_osm):
    if way.id() not in other_osm.ways:
        other_osm.add_way(way)
        for node_id in way.nodes:
            if not node_id in other_osm.nodes:
                node = source_osm.nodes[node_id]
                other_osm.add_node(node)


def print_usage(error=""):
    if error: print "ERROR:", error
    print "USAGE: %s buildins-with-tag-segmented.osm" % (sys.argv[0],)
    if error:
        return -1
    else:
        return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

