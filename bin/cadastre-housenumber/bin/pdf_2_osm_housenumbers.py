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


import os
import sys
import os.path

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from cadastre_fr.tools      import toposort
from cadastre_fr.tools      import command_line_error
from cadastre_fr.parser     import CadastreParser
from cadastre_fr.globals    import SOURCE_TAG
from cadastre_fr.geometry   import Point
from cadastre_fr.geometry   import Path
from cadastre_fr.geometry   import BoundingBox
from cadastre_fr.transform  import PDFToCadastreTransform
from cadastre_fr.transform  import CadastreToOSMTransform
from cadastre_fr.recognizer import HousenumberPathRecognizer


def write_osm_for_housenumbers(output, osm_bbox, housenumbers):
    #osm_bbox = BoundingBox.of_points(housenumbers.keys())
    output.write("<?xml version='1.0' encoding='UTF-8'?>\n")
    output.write("<osm version='0.6' generator='%s' upload='false'>\n" % (sys.argv[0],))
    id = 0;
    for number, position, angle in housenumbers:
        id = id-1;
        output.write("  <node id='%d' lon='%f' lat='%f'>\n" % 
                     (id, position.x, position.y))
        output.write("    <tag k='addr:housenumber' v='%s' />\n" 
                     % (number,))
        output.write((u"    <tag k='source' v='" + SOURCE_TAG + "' />\n").encode("utf-8"))
        output.write(u"    <tag k='fixme' v='À vérifier et associer à la bonne rue' />\n".encode("utf-8"))
        output.write("  </node>\n")
    output.write("</osm>\n")


       

def pdf_2_projection_and_housenumbers(pdf_filename_list):
    housenumber_recognizer = HousenumberPathRecognizer()
    cadastre_parser = CadastreParser([housenumber_recognizer.handle_path])
    for pdf_filename in pdf_filename_list:
        cadastre_parser.parse(pdf_filename)
    return cadastre_parser.cadastre_projection, housenumber_recognizer.housenumbers

def pdf_2_osm_housenumbers(pdf_filename_list, osm_output):
    cadastre_projection, cadastre_housenumbers = \
            pdf_2_projection_and_housenumbers(pdf_filename_list)
    cadastre_to_osm_transform = CadastreToOSMTransform(cadastre_projection).transform_point
    osm_housenumbers = [
        (value, cadastre_to_osm_transform(position),angle) for (value, position,angle) in
          cadastre_housenumbers]
    write_osm_for_housenumbers(osm_output, None, osm_housenumbers)
    osm_output.flush()

HELP_MESSAGE = "USAGE: {0} fichier.pdf+ [fichier.osm]".format(sys.argv[0])

def main(argv):
    if (len(argv) < 2): 
        command_line_error(u"fichier .pdf non spécifié", HELP_MESSAGE)
    pdf_filename_list = sys.argv[1:]
    if pdf_filename_list[-1].endswith(".osm"):
        osm_output = open(pdf_filename_list.pop(),"w")
    else:
        osm_output = sys.stdout
    for f in pdf_filename_list:
        if (not f.endswith(".svg")) and (not f.endswith(".pdf")):
            command_line_error(u"l'argument n'est pas un fichier .pdf ou .svg: " + f)
        if not os.path.exists(f):
            command_line_error("fichier non trouvé: " + f)
        bboxfile = f[:-4] + ".bbox"
        if not os.path.exists(bboxfile):
            command_line_error(u"fichier .bbox correspondant non trouvé: " + bboxfile)
    pdf_2_osm_housenumbers(pdf_filename_list, osm_output)
    

if __name__ == '__main__':
    main(sys.argv)


