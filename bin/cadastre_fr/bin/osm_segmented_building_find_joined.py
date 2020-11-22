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
Compare deux fichiers .osm pour trouver les buildings du premier
qui sont fusionés dans le deuxième.
Génère un trosième fichier, copie du premier avec un nouveau tag
"segmented" contenant l'id de building fusionné dans le deuxième.
(ou "no" si non fusioné ou "?" si building pas clairement trouvé
dans le deuxième fichier)
"""


import sys
import os.path

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.osm        import OsmParser
from cadastre_fr.osm        import OsmWriter
from cadastre_fr.tools      import command_line_error
from cadastre_fr.segmented  import find_joined_and_unmodified_buildings

TOLERANCE = 0.5 # distance en metre de tolérance du buffer pour considérer un building inclus dans un autre


HELP_MESSAGE = "USAGE: {0} houses-segmente.osm buildings-corrected.osm".format(sys.argv[0])

def main(argv):
    if len(argv) == 2 and len(argv[1]) == 5:
        prefix = argv[1]
        if os.path.exists(prefix + "-houses-simplifie.osm"):
            segmented_osm_file = prefix + "-houses-simplifie.osm"
        elif os.path.exists(prefix + "-houses.osm"):
            segmented_osm_file = prefix + "-houses.osm"
        else:
            command_line_error("no prefix-houses.osm file found", HELP_MESSAGE)
        if os.path.exists(prefix + "-buildings.osm"):
            corrected_osm_file = prefix + "-buildings.osm"
        else:
            command_line_error("no prefix-buildings.osm file found", HELP_MESSAGE)
        other_args = []
    else:
        osm_args = [f for f in argv[1:] if os.path.splitext(f)[1] == ".osm"]
        if len(osm_args) == 2:
            segmented_osm_file,  corrected_osm_file  = osm_args
        elif len(osm_args) < 2:
            command_line_error("not enough .osm arguments", HELP_MESSAGE)
        else:
            command_line_error("too many .osm arguments", HELP_MESSAGE)
        other_args = [f for f in argv[1:] if os.path.splitext(f)[1] not in (".osm")]
        if len(other_args) != 0:
            command_line_error("invalid argument: " + other_args[0], HELP_MESSAGE)
        prefix = os.path.commonprefix(osm_args)
    print(("load " + segmented_osm_file))
    segmented_osm = OsmParser().parse(segmented_osm_file)
    print(("load " + corrected_osm_file))
    corrected_osm = OsmParser().parse(corrected_osm_file)
    print("find joined buildings")
    joined, unmodified = find_joined_and_unmodified_buildings(segmented_osm, corrected_osm, TOLERANCE)
    #joined_osm     = osm_filter_items(segmented_osm, itertools.chain(*joined))
    #unmodified_osm = osm_filter_items(segmented_osm, unmodified)
    #OsmWriter(joined_osm).write_to_file(os.path.splitext(corrected_osm_file)[0] + "-joined.osm")
    #OsmWriter(unmodified_osm).write_to_file(os.path.splitext(corrected_osm_file)[0] + "-unmodified.osm")
    output_file = os.path.splitext(segmented_osm_file)[0] + "-joined.osm"
    print(("save " + output_file))
    OsmWriter(segmented_osm).write_to_file(output_file)
    return 0





if __name__ == '__main__':
    sys.exit(main(sys.argv))

