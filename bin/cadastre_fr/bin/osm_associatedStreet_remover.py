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



""" Supprime d'un fichier OSM les relations associatedStreet,
    et modifie les éléments 'house' associés pour leur
    positionner le tag addr:street avec l'ancien nom
    de l'associatedStreet.
"""

import sys
import zipfile
import os.path
from io import StringIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.osm import Osm, OsmWriter, OsmParser
from cadastre_fr.tools import command_line_error


HELP_MESSAGE = """Supprime les relations associatedStreet et positionne le tag addr:street des nœuds 'house' associés avec l'ancien nom de la relation.
USAGE:
{0}  input.osm output.osm
{0}  input.zip output.zip""".format(sys.argv[0])

def osm_remove_associatedstreet(osm):
    for rid,relation in list(osm.relations.items()):
        if relation.tags.get('type') == 'associatedStreet' and 'name' in relation.tags:
            for member in relation.members:
                if member.get('role') == 'house':
                    housenumber = None
                    if member['type'] == 'way':
                        housenumber = osm.ways[int(member['ref'])]
                    elif member['type'] == 'node':
                        housenumber = osm.nodes[int(member['ref'])]
                    if housenumber and 'addr:street' not in housenumber.tags:
                        housenumber.tags['addr:street'] = relation.tags['name']
            del(osm.relations[rid])


def osm_file_remove_associatedstreet(inputfile, outputfile):
    osm = OsmParser().parse(inputfile)
    osm_remove_associatedstreet(osm)
    OsmWriter(osm).write_to_file(outputfile)


def osm_zip_remove_associatedstreet(inputfile, outputfile):
    inputzip = zipfile.ZipFile(inputfile, "r")
    outputzip = zipfile.ZipFile(outputfile, "w", zipfile.ZIP_DEFLATED)
    for name in inputzip.namelist():
        if name.endswith(".osm"):
            osm = OsmParser().parse_stream(inputzip.open(name),name)
            osm_remove_associatedstreet(osm)
            s = StringIO()
            OsmWriter(osm).write_to_stream(s)
            outputzip.writestr(name, s.getvalue())
        else:
            outputzip.writestr(name, inputzip.open(name).read())
    inputzip.close()
    outputzip.close()


def main(argv):
    args_extensions = set([os.path.splitext(p)[1] for p in sys.argv[1:]])
    if len(argv) != 3 or (args_extensions != set([".osm"]) and args_extensions != set([".zip"])):
        command_line_error("arguments invalides", HELP_MESSAGE)
    inputfile, outputfile = argv[1:3]
    if inputfile.endswith(".zip"):
        osm_zip_remove_associatedstreet(inputfile, outputfile)
    else:
        osm_file_remove_associatedstreet(inputfile, outputfile)

if __name__ == '__main__':
    main(sys.argv)

