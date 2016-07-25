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


import sys
import os.path
from glob import glob

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from cadastre_fr.osm       import OsmWriter
from cadastre_fr.building  import pdf_2_osm_buildings


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
        cadastre_buildings = pdf_2_osm_buildings(pdf_args)
        cadastre_buildings.update_bbox()
        OsmWriter(cadastre_buildings).write_to_file(prefix + "-houses.osm")
    return 0




if __name__ == '__main__':
    sys.exit(main(sys.argv))

