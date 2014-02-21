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



""" Supprime d'un fichier OSM les relations associatedStreet,
    et modifie les éléments 'house' associés pour leur
    positionner le tag addr:street avec l'ancien nom
    de l'associatedStreet.
"""

import sys
import zipfile
from cStringIO import StringIO

from osm import Osm, OsmWriter, OsmParser


def print_help():
    programme = sys.argv[0]
    spaces = " " * len(programme)
    sys.stdout.write((u"Supprime les relations associatedStreet et positionne le tag addr:street des nœuds 'house' associés avec l'ancien nom de la relation.\n").encode("utf-8"))
    sys.stdout.write((u"USAGE:" + "\n").encode("utf-8"))
    sys.stdout.write((u"%s  input.osm output.osm\n" % programme ).encode("utf-8"))
    sys.stdout.write((u"%s  input.zip output.zip\n" % programme ).encode("utf-8"))

def osm_remplace_associatedstreet_par_addrstreet(osm):
    for rid,relation in osm.relations.items():
        if relation.tags.get('type') == 'associatedStreet' and relation.tags.has_key('name'):
            for member in relation.members:
                if member.get('role') == 'house':
                    housenumber = None
                    if member['type'] == 'way':
                        housenumber = osm.ways[int(member['ref'])]
                    elif member['type'] == 'node':
                        housenumber = osm.nodes[int(member['ref'])]
                    if housenumber and not housenumber.tags.has_key('addr:street'):
                        housenumber.tags['addr:street'] = relation.tags['name']
            del(osm.relations[rid])

def remplace_associatedstreet_par_addrstreet(inputfile, outputfile):
    if inputfile.endswith(".osm"):
        assert(outputfile.endswith(".osm"))
        osm = OsmParser().parse(inputfile)
        osm_remplace_associatedstreet_par_addrstreet(osm)
        OsmWriter(osm).write_to_file(outputfile)
    elif inputfile.endswith(".zip"):
        assert(outputfile.endswith(".zip"))
        inputzip = zipfile.ZipFile(inputfile, "r")
        outputzip = zipfile.ZipFile(outputfile, "w", zipfile.ZIP_DEFLATED)
        for name in inputzip.namelist():
            if name.endswith(".osm"):
                osm = OsmParser().parse_stream(inputzip.open(name),name)
                #osm = OsmParser().parse_data(data,name)
                osm_remplace_associatedstreet_par_addrstreet(osm)
                s = StringIO()
                #OsmWriter(osm).write_to_file(name + ".2")
                OsmWriter(osm).write_to_stream(s)
                #print s.getvalue()
                outputzip.writestr(name, s.getvalue())
            else:
                outputzip.writestr(name, inputzip.open(name).read())
        inputzip.close()
        outputzip.close()
    else:
        raise Exception("unknown file type: " + inputfile)

    

def main(argv):
    if len(argv) != 3:
       print_help()
    else:
       remplace_associatedstreet_par_addrstreet(argv[1],argv[2])

if __name__ == '__main__':
    main(sys.argv)

