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
    svg_vers_osm_housenumbers.py
car celui-ci ignore les éléments <g> (et leur transform associée)
"""


import sys
import xml.parsers.expat
import xml.sax.saxutils

# Dans le référenciel du cadastre, les coordonnées y sont inversées:
INVERSE_HAUT_BAS= False

class SVG_G_Filter(object):
    """ Enleve les groupe <g> depuis un fichier SVG"""
    def __init__(self):
        self.parser = xml.parsers.expat.ParserCreate()
        self.parser.StartElementHandler = self.handle_start_element
        self.parser.EndElementHandler = self.handle_end_element
        self.parser.CharacterDataHandler = self.handle_char_data
    def parse(self, input_file, output_file):
        self.output = output_file
        output_file.write('<?xml version="1.0"?>\n')
        self.parser.ParseFile(input_file)
        input_file.close()
        output_file.close()
    def handle_start_element(self, name, attrs):
        if name.lower() != "g": 
            self.output.write(("\n  ".join(
                ["\n<" + name] + 
                [ n + "=" + xml.sax.saxutils.quoteattr(v)
                  for n,v in attrs.items()])
            + ">").encode("utf8"))
        if INVERSE_HAUT_BAS and (name.lower() == "svg"):
            # Début du fichier, crée un groupe pour inverser les coordonnées y:
            self.output.write("\n<g transform='matrix(1,0,0,-1,0,0)'>\n")
    def handle_end_element(self, name):
        if INVERSE_HAUT_BAS and (name.lower() == "svg"):
            self.output.write("\n</g>\n")
        if name.lower() != "g":
            self.output.write("</" + name + ">\n".encode("utf8"))
    def handle_char_data(self, data):
        self.output.write(xml.sax.saxutils.escape(data).encode("utf8"))

def main(argv):
  if len(argv) in [2,3]:
      input_file = open(argv[1])
      if len(argv) > 2:
          output_file = open(argv[2],"w")
      else:
          output_file = sys.stdout

      SVG_G_Filter().parse(input_file, output_file)
  else:
      print "USAGE: " + argv[0] + " input_file.svg output_file.svg"

if __name__ == '__main__':
    main(sys.argv)
