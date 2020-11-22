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

# Partitionne les noeuds d'un fichier osm en groupes de taille équivalente.

import os
import sys
import math
import os.path
import zipfile
from io import StringIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import bbox_2_osm
from cadastre_fr.osm             import *
from cadastre_fr.geometry        import BoundingBox
from cadastre_fr.tools           import command_line_error
from cadastre_fr.partitioning    import partition_osm_nodes


HELP_MESSAGE = "USAGE: {0} input.osm  [size [output.zip]]".format(sys.argv[0])


def main(argv):
    if (len(sys.argv) < 2):
        command_line_error("fichier .osm non spécifié", HELP_MESSAGE)
    input_filename = sys.argv[1]
    input_basename = os.path.splitext(os.path.basename(input_filename))[0]
    if len(sys.argv) < 3:
      size = 50
    elif not (sys.argv[2].isdigit()):
        command_line_error("invalid size format", HELP_MESSAGE)
    else:
      size = int(sys.argv[2])
    if len(sys.argv) >= 4:
      output_filename = sys.argv[3]
    else:
      output_filename = os.path.splitext(input_filename)[0] + ("-partition%d.zip" % size)
    if len(sys.argv) > 4:
        command_line_error("trop d'arguments", HELP_MESSAGE)
    print(("Lecture de " + input_filename))
    input_osm = OsmParser().parse(input_filename)
    input_bbox = input_osm.bbox()
    if len(input_osm.ways) > 0 or len(input_osm.relations) > 0:
      command_line_error("le fichier %s ne contient pas que des noeuds" % input_filename, HELP_MESSAGE)
    print("Partitionnement...")
    if (len(input_osm.nodes) > size):
      partitions = partition_osm_nodes(list(input_osm.nodes.values()), size)
    else:
      partitions = [(list(input_osm.nodes.values()), input_bbox),]
    print((" -> %d partitions" % (len(partitions))))
    print(("Écriture de " + output_filename))
    zip_output = zipfile.ZipFile(output_filename,"w", zipfile.ZIP_DEFLATED)
    index_size = int(math.ceil(math.log10(len(partitions))))
    bboxes = {}
    for i in range(len(partitions)):
      nodes, bbox = partitions[i]
      p_name = ("partition_%%0%dd" % index_size) % i
      bboxes[p_name] = BoundingBox(*bbox)
      p_osm = Osm(input_osm.attrs.copy())
      list(map(p_osm.add_node, nodes))
      s = StringIO()
      OsmWriter(p_osm).write_to_stream(s)
      zip_output.writestr(input_basename + "-" + p_name + ".osm", s.getvalue())
    s = StringIO()
    bbox_2_osm.write_osm_for_boxes(s, BoundingBox(*input_bbox), bboxes)
    zip_output.writestr(input_basename + "-index.osm", s.getvalue())
    zip_output.close()


if __name__ == '__main__':
    main(sys.argv)


