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


import sys
import os.path
import xml.parsers.expat
import xml.sax.saxutils

# Dans le référenciel du cadastre, les coordonnées y sont inversées:

class SvgGroupRemover(object):
    """ Enleve les groupe <g> depuis un fichier SVG"""
    def __init__(self, INVERT_Y_AXIS = False):
        self.parser = xml.parsers.expat.ParserCreate()
        self.parser.StartElementHandler = self.handle_start_element
        self.parser.EndElementHandler = self.handle_end_element
        self.parser.CharacterDataHandler = self.handle_char_data
        self.INVERT_Y_AXIS = INVERT_Y_AXIS
    def filter(self, input_file, output_file):
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
        if self.INVERT_Y_AXIS and (name.lower() == "svg"):
            # Début du fichier, crée un groupe pour inverser les coordonnées y:
            self.output.write("\n<g transform='matrix(1,0,0,-1,0,0)'>\n")
    def handle_end_element(self, name):
        if self.INVERT_Y_AXIS and (name.lower() == "svg"):
            self.output.write("\n</g>\n")
        if name.lower() != "g":
            self.output.write("</" + name + ">\n".encode("utf8"))
    def handle_char_data(self, data):
        self.output.write(xml.sax.saxutils.escape(data).encode("utf8"))

def pdf_2_svg(pdf_filename):
    svg_filename = os.path.splitext(pdf_filename)[0] + ".svg"
    if not (os.path.exists(svg_filename) and os.path.exists(svg_filename + ".ok") and (os.path.getmtime(svg_filename) > os.path.getmtime(pdf_filename))):
        if os.path.exists(svg_filename + ".ok"): os.remove(svg_filename + ".ok")
        svg_sans_groupes_filename = os.path.splitext(pdf_filename)[0] + "-sans_groupes.svg"
        cmd = 'inkscape --without-gui' \
            + ' "--file=' + pdf_filename + '"'\
            + ' "--export-plain-svg=' + svg_filename + '"'
        sys.stdout.write(cmd + "\n")
        sys.stdout.flush()
        if os.system(cmd) != 0:
          raise Exception("impossible d'exécuter inkscape")
        # Crée une version du fichier sans groupes:
        SvgGroupRemover().filter(open(svg_filename), open(svg_sans_groupes_filename,"w"))
        open(svg_filename + ".ok", 'a').close()
    return svg_filename



def pdfs_2_svgs(pdf_filename_list):
    return [pdf_2_svg(pdf) for pdf in pdf_filename_list]


