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

Utilise le classifier généré par osm_segmented_building_train.py
pour prédire si des bâtiments devraient être plutot fusionnés.
(cad si il ont été potentiellement fractionnés de manière injustifiée
 par le cadastre)

"""


import sys
import os.path

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.osm        import OsmParser
from cadastre_fr.osm        import OsmWriter
from cadastre_fr.tools      import command_line_error
from cadastre_fr.simplify   import simplify
from cadastre_fr.transform  import get_centered_metric_equirectangular_transformation_from_osm
from cadastre_fr.segmented  import compute_transformed_position_and_annotate
from cadastre_fr.segmented  import get_predicted_segmented_buildings
from cadastre_fr.segmented  import load_classifier_and_scaler
from cadastre_fr.segmented  import filter_buildings_junction
from cadastre_fr.globals    import VERBOSE

HELP_MESSAGE = "USAGE: {0} houses.osm".format(sys.argv[0])

def main(argv):
  args = argv[1:]
  global VERBOSE
  i = 0
  while i < (len(args) - 1):
    if args[i] == "-v":
      VERBOSE=True
      del(args[i])
    else:
      i = i + 1
  if len(args) == 0 or len(args) > 2 or any([arg.startswith("-") for arg in args]):
      command_line_error("wrong argument", HELP_MESSAGE)
  else:
    input_filename = args[0]
    if len(args) > 1:
      output_filename = args[1]
    else:
      name,ext = os.path.splitext(input_filename)
      output_filename = name + "-prediction_segmente" + ext

    if VERBOSE: print(("load " + input_filename + " ..."))

    osm = OsmParser().parse(input_filename)
    #simplify(osm, 0.2, 0.2, 0.1)

    if VERBOSE: print("transform...")

    if osm.bbox():
      inputTransform, outputTransform = get_centered_metric_equirectangular_transformation_from_osm(osm)
      compute_transformed_position_and_annotate(osm, inputTransform)

    if VERBOSE: print("detect...")
    classifier, scaler = load_classifier_and_scaler()
    buildings = get_predicted_segmented_buildings(classifier, scaler, osm)
    if VERBOSE: print((" -> ", len(buildings), "cas"))

    output_osm = filter_buildings_junction(osm, buildings)

    if len(output_osm.nodes) > 0:
        if VERBOSE: print(("save ", output_filename))
        OsmWriter(output_osm).write_to_file(output_filename)
    else:
        print("Nothing detected")

    return 0



if __name__ == '__main__':
    sys.exit(main(sys.argv))

