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



""" Conversion pdf en svg en utilisant inkscape """

import sys
import os.path

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from cadastre_fr.tools import command_line_error
from cadastre_fr.svg   import pdfs_2_svgs


HELP_MESSAGE = u"""Conversion pdf en svg
USAGE: {0} fichier.pdf [fichier2.pdf ...]\n""".format(sys.argv[0])


def main(argv):
    if len(argv) <= 1: 
        command_line_error(u"pas asser d'argument", HELP_MESSAGE)
    elif argv[1] in ["-h", "-help","--help"]:
        print_help()
    else:
        pdf_filename_list = sys.argv[1:]
        for f in pdf_filename_list:
            if not f.endswith(".pdf"):
                command_line_error(u"l'argument n'est pas un fichier .pdf: " + f)
                return
        pdfs_2_svgs(pdf_filename_list)

if __name__ == '__main__':
    main(sys.argv)


