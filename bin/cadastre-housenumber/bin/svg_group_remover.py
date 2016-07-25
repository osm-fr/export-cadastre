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
Enlève les groupes <g></g> d'un fichier svg,
cela lui donne la meme apparence que celle vue par le programme
    svg_2_osm_housenumbers.py
car celui-ci ignore les éléments <g> (et leur transform associée)
"""


import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from cadastre_fr.svg import SvgGroupRemover

def main(argv):
  if len(argv) in [2,3]:
      input_file = open(argv[1])
      if len(argv) > 2:
          output_file = open(argv[2],"w")
      else:
          output_file = sys.stdout

      SvgGroupRemover().filter(input_file, output_file)
  else:
      print "USAGE: " + argv[0] + " input_file.svg output_file.svg"

if __name__ == '__main__':
    main(sys.argv)
