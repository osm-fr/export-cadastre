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

""" Tente d'extraire les mots (nom de rue ou de lieu)
    depuis le cadastre au format pdf.
"""


import sys
import os.path

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.tools  import command_line_error
from cadastre_fr.name   import pdf_2_osm_names


HELP_MESSAGE = "USAGE: %s fichier.pdf+ [fichier.osm]\n" % sys.argv[0]

def main(argv):
    if (len(argv) < 2):
        command_line_error("fichier .pdf non spécifié", HELP_MESSAGE)
    pdf_filename_list = sys.argv[1:]
    if pdf_filename_list[-1].endswith(".osm"):
        osm_output = open(pdf_filename_list.pop(),"w")
    else:
        osm_output = sys.stdout
    for f in pdf_filename_list:
        if (not f.endswith(".svg")) and (not f.endswith(".pdf")):
            command_line_error("l'argument n'est pas un fichier .pdf ou .svg: " + f, HELP_MESSAGE)
        if not os.path.exists(f):
            command_line_error("fichier non trouvé: " + f, HELP_MESSAGE)
        bboxfile = f[:-4] + ".bbox"
        if not os.path.exists(bboxfile):
            command_line_error("fichier .bbox correspondant non trouvé: " + bboxfile, HELP_MESSAGE)
    pdf_2_osm_names(pdf_filename_list, osm_output)


if __name__ == '__main__':
    main(sys.argv)


