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


import sys
import os.path

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.osm        import OsmParser
from cadastre_fr.osm        import OsmWriter
from cadastre_fr.tools      import command_line_error
from cadastre_fr.tools      import open_zip_and_files_with_extension
from cadastre_fr.transform  import get_centered_metric_equirectangular_transformation_from_osm
from cadastre_fr.segmented  import compute_transformed_position_and_annotate
from cadastre_fr.segmented  import load_classifier_and_scaler
from cadastre_fr.segmented  import test_classifier
from cadastre_fr.globals    import VERBOSE


HELP_MESSAGE = "USAGE: {0} buildins-with-tag-segmented.osm".format(sys.argv[0])


def main(argv):
    global VERBOSE
    VERBOSE = True
    osm_args = [f for f in argv[1:] if os.path.splitext(f)[1] in (".zip", ".osm")]
    other_args = [f for f in argv[1:] if os.path.splitext(f)[1] not in (".zip", ".osm")]
    if len(other_args) != 0:
        command_line_error("invalid argument: " + other_args[0], HELP_MESSAGE)
    if len(osm_args) == 0:
        command_line_error("not enough file.osm args", HELP_MESSAGE)

    classifier, scaler = load_classifier_and_scaler()

    score = 0

    for name, stream in open_zip_and_files_with_extension(osm_args, ".osm"):
        if VERBOSE: print "load " + name
        input_osm = OsmParser().parse_stream(stream)
        inputTransform, outputTransform = get_centered_metric_equirectangular_transformation_from_osm(input_osm)
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



if __name__ == '__main__':
    sys.exit(main(sys.argv))

