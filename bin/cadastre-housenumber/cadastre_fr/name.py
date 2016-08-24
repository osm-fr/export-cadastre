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


import math
import zipfile
from cStringIO import StringIO

from .osm        import Osm, Node, Way, OsmWriter
from .osm_tools  import osm_add_point
from .osm_tools  import osm_add_way_direction
from .tools      import command_line_error
from .tools      import iteritems
from .parser     import CadastreParser
from .transform  import CadastreToOSMTransform
from .recognizer import TextPathRecognizer
from .recognizer import NamePathRecognizer
from .globals    import SOURCE_TAG



def pdf_2_names(pdf_filename_list):
    names_recognizer = NamePathRecognizer()
    cadastre_parser = CadastreParser([names_recognizer.handle_path])
    for pdf_filename in pdf_filename_list:
        cadastre_parser.parse(pdf_filename)
    return cadastre_parser.cadastre_projection, names_recognizer.lieuxdits, names_recognizer.street_names, names_recognizer.small_names

def pdf_2_osm_names(pdf_filename_list, osm_output):
    projection, lieuxdits_names, street_names, small_names = pdf_2_names(pdf_filename_list)
    cadastre_to_osm_transform = CadastreToOSMTransform(projection).transform_point
    osm = generate_osm_names(lieuxdits_names, street_names, small_names, cadastre_to_osm_transform)
    OsmWriter(osm).write_to_stream(osm_output)


def generate_osm_names(lieuxdits_names, street_names, small_names, transform):
    osm = Osm({'upload':'false'})
    for name, position, angle in lieuxdits_names:
        node = osm_add_point(osm, position, transform)
        node.tags['name'] = name
        if name.lower().startswith("hameau "):
            node.tags['place'] = 'hamlet'
        else:
            node.tags['place'] = ''
        node.tags['source'] = SOURCE_TAG
        angle_deg = int(round(angle * 180 / math.pi)) # rad -> deg arrondi
        if angle_deg != 0:
            osm_add_way_direction(osm, node, position, angle, len(name), transform)
    for name, position, angle in street_names:
        node = osm_add_point(osm, position, transform)
        node.tags['name'] = name
        node.tags['source'] = SOURCE_TAG
        angle_deg = int(round(angle * 180 / math.pi)) # rad -> deg arrondi
        node.tags['angle'] = str(angle_deg) + u"°"
        if angle_deg != 0:
            osm_add_way_direction(osm, node, position, angle, len(name), transform)
    for name, position, angle in small_names:
        node = osm_add_point(osm, position, transform)
        node.tags['name'] = name
        node.tags['small'] = "yes"
        node.tags['source'] = SOURCE_TAG
        angle_deg = int(round(angle * 180 / math.pi)) # rad -> deg arrondi
        node.tags['angle'] = str(angle_deg) + u"°"
        if angle_deg != 0:
            osm_add_way_direction(osm, node, position, angle, len(name), transform)
    return osm



def generate_osm_lieuxdits_names(names, transform):
    osm = Osm({'upload':'false'})
    for name, position, angle in names:
        node = osm_add_point(osm, position, transform)
        node.tags['name'] = name
        node.tags['source'] = SOURCE_TAG
        angle_deg = int(round(angle * 180 / math.pi)) # rad -> deg arrondi
        if angle_deg != 0:
            osm_add_way_direction(osm, node, position, angle, len(name), transform)
    return osm

def generate_osm_street_names(names, transform):
    osm = Osm({'upload':'false'})
    for name, position, angle in names:
        angle_deg = int(round(angle * 180 / math.pi)) # rad -> deg arrondi
        # exclue les lettres uniques (len=1) écrites à l'horizontal (angle=0)
        if (len(name) > 1) or (angle_deg != 0):
            node = osm_add_point(osm, position, transform)
            node.tags['name'] = name
            node.tags['source'] = SOURCE_TAG
            if angle_deg != 0:
                osm_add_way_direction(osm, node, position, angle, len(name), transform)
            #pos1 = (position[0] - len(name) * math.cos(angle), 
            #        position[1] - len(name) * math.sin(angle))
            #pos2 = (position[0] + len(name) * math.cos(angle), 
            #        position[1] + len(name) * math.sin(angle))
            #p1 = osm_add_point(osm, pos1, transform)
            #p2 = osm_add_point(osm, pos2, transform)
            #way = osm_add_nodes_way(osm, [p1, p2])
            #way.tags['name'] = name
            #way.tags['source'] = SOURCE_TAG
            #way.tags['highway'] = "unclassified"
    return osm

def generate_osm_small_names(names, transform):
    osm = Osm({'upload':'false'})
    for name, position, angle in names:
        node = osm_add_point(osm, position, transform)
        node.tags['name'] = name
        node.tags['source'] = SOURCE_TAG
        angle_deg = int(round(angle * 180 / math.pi)) # rad -> deg arrondi
        if angle_deg != 0:
            osm_add_way_direction(osm, node, position, angle, len(name), transform)
    return osm

def zip_osm_names(osm_lieuxdits_names, osm_street_names, osm_small_names, zip_filename, subdir=""):
    if subdir: subdir += "/"
    filename_osm_map = {}
    filename_osm_map[subdir + "mots_lieux-dits_-_NE_PAS_ENVOYER_SUR_OSM.osm"] = osm_lieuxdits_names
    filename_osm_map[subdir + "mots_rues_-_NE_PAS_ENVOYER_SUR_OSM.osm"] = osm_street_names
    filename_osm_map[subdir + "petits_mots_-_NE_PAS_ENVOYER_TEL_QUEL_SUR_OSM.osm"] = osm_small_names
    zip_output = zipfile.ZipFile(zip_filename,"w", zipfile.ZIP_DEFLATED)
    for filename, osm in iteritems(filename_osm_map):
        s = StringIO()
        OsmWriter(osm).write_to_stream(s)
        zip_output.writestr(filename, s.getvalue())
    zip_output.writestr(subdir + "LISEZ-MOI.txt", """Ces fichiers contiennent des mots positionnes a l'endroit\r\nou ils sont dessines sur le cadastre.\r\nIls peuvent etre utilises comme sources d'information pour\r\ncompleter OpenStreetMap, mais ils ne doivent surtout\r\npas etre envoyes tels quels vers OSM.""") 
    zip_output.close()

