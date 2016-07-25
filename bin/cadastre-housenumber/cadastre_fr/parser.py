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


"""Parser for PDF files from the cadastre."""

import sys
import os.path
import subprocess

from cadastre_fr.geometry  import Path
from cadastre_fr.geometry  import BoundingBox
from cadastre_fr.transform import PDFToCadastreTransform

THIS_DIR = os.path.dirname(__file__)
PDFPARSER = os.path.join(THIS_DIR, "..", "pdfparser", "pdfparser")


if not os.path.exists(PDFPARSER):
  sys.stderr.write(u"ERREUR: le programme pdfparser n'as pas été trouvé.\n".encode("utf-8"))
  sys.stderr.write(u"        Veuillez executer la commande suivante et relancer:\n".encode("utf-8"))
  sys.stderr.write(u"    make\n".encode("utf-8"))
  sys.exit(-1)



class CadastreParser(object):
    """ Parse un fichier PDF obtenue depuis le cadastre,
        pour y trouver les <path> 
        Les path qui nous intéressent sont tous dans le même groupe <g>,
        donc on ignore completement les transformations de
        coordonées (pdf transform).
    """
    def __init__(self, path_handlers = None):
        self.path_handlers = path_handlers if path_handlers else []
    def add_path_handler(self, path_handler):
        self.path_handlers.append(handler)
    def parse(self, filename):
        bbox_filename = os.path.splitext(filename)[0]  + ".bbox"
        self.cadastre_projection, cadastre_bbox = open(bbox_filename).read().split(":")
        self.cadastre_bbox = BoundingBox(*[float(v) for v in cadastre_bbox.split(",")])
        self.pdf_bbox = None

        ext = os.path.splitext(filename)[1]

        if ext == ".svg":
            parser = xml.parsers.expat.ParserCreate()
            parser.StartElementHandler = self.handle_start_element
            parser.ParseFile(open(filename))
        elif ext == ".pdf":
            pipe = subprocess.Popen([PDFPARSER, filename], 
                    bufsize=128*1024, stdout=subprocess.PIPE).stdout
            while True:
                line = pipe.readline()
                if not line:
                    break
                path = Path.from_svg(line.rstrip())
                path.style = pipe.readline().rstrip()
                self.handle_path(path)
        else:
            raise Exception("not a pdf or svg filename: " + filename)

    def handle_start_element(self, name, attrs):
        name = name.lower()
        if name.lower() == "path":
            path = Path.from_svg(attrs["d"])
            if "style" in attrs:
                path.style = attrs["style"].replace(" ","")
            self.handle_path(path)

    def handle_path(self, path):
        if self.pdf_bbox == None:
            # Try to find the bbox (a white rectangle)
            if (path.commands == "MLLLLZ"
                    and "fill:#ffffff" in path.style.split(";")):
                self.pdf_bbox = path.bbox()
                self.pdf_to_cadastre_transform = PDFToCadastreTransform(self.pdf_bbox, self.cadastre_bbox).transform_point
                #sys.stdout.write("pdf bbox:" + str(self.bbox) + "\n")
        else:          
            for path_handler in self.path_handlers:
                if path_handler(path, self.pdf_to_cadastre_transform):
                    break



