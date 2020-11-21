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

"""
Import des pdf depuis le cadastre (https://cadastre.gouv.fr)

ATTENTION: l'utilisation des données du cadastre n'est pas libre, et ce script doit
donc être utilisé exclusivement pour contribuer à OpenStreetMap, voire
http://wiki.openstreetmap.org/wiki/Cadastre_Fran%C3%A7ais/Conditions_d%27utilisation

Ce script est inspiré du programme Qadastre de Pierre Ducroquet
(https://gitorious.org/qadastre/qadastre2osm/)
et du script import-bati.sh
(http://svn.openstreetmap.org/applications/utils/cadastre-france/import-bati.sh)

"""

import re
import sys
import time
import os.path

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.tools import write_string_to_file
from cadastre_fr.tools import write_stream_to_file
from cadastre_fr.tools import command_line_error
from cadastre_fr.website import CadastreWebsite
from cadastre_fr.website import command_line_open_cadastre_website
from cadastre_fr.geometry import BoundingBox
from cadastre_fr.transform import OSMToCadastreTransform
from cadastre_fr.download_pdf import download_pdfs
from cadastre_fr.download_pdf import PDF_DOWNLOAD_PIXELS_RATIO
from cadastre_fr.download_pdf import PDF_DOWNLOAD_SPLIT_MODE
from cadastre_fr.download_pdf import PDF_DOWNLOAD_SPLIT_NB
from cadastre_fr.download_pdf import PDF_DOWNLOAD_SPLIT_SIZE
from cadastre_fr.download_pdf import PDF_DOWNALOD_WAIT_SECONDS

BBOX_OPTION_FORMAT = re.compile("^(-?[0-9]*(\\.[0-9]*)?,){3}-?[0-9]*(\\.[0-9]*)?$")


HELP_MESSAGE = """Téléchargement de PDF du cadastre
OPTIONS:
    -nb <int>      : découpage par un nombre fixe
    -size <int>    : découpage par une taille fixe (en mètres)
    -ratio <float> : Nombre de pixels / mètre des PDF exportés
    -wait <seconds>: attente en seconde entre chaque téléchargement
    -bbox lon1,lat1,lon2,lat2: restreint la zone a extraire
USAGE:
{0}  DEPARTEMENT COMMUNE
           télécharge les export PDFs du cadastre d'une commune.
{0}
           liste les départements
{0}  DEPARTEMENT
           liste les communes d'un département""".format(sys.argv[0])



def cadastre_2_pdfs(argv):
  i = 1
  ratio=PDF_DOWNLOAD_PIXELS_RATIO
  mode=PDF_DOWNLOAD_SPLIT_MODE
  nb=PDF_DOWNLOAD_SPLIT_NB
  size=PDF_DOWNLOAD_SPLIT_SIZE
  wait=PDF_DOWNALOD_WAIT_SECONDS
  bbox=None
  while i < len(argv):
      if argv[i].startswith("-"):
          if argv[i] in ["-h", "-help","--help"]:
              command_line_error(None, HELP_MESSAGE)
          elif argv[i] in ["-r", "-ratio","--ratio"]:
              ratio = float(argv[i+1])
              del(argv[i:i+2])
          elif argv[i] in ["-s", "-size","--size"]:
              size = int(argv[i+1])
              mode = "SIZE"
              del(argv[i:i+2])
          elif argv[i] in ["-n", "-nb","--nb"]:
              nb = int(argv[i+1])
              mode = "NB"
              del(argv[i:i+2])
          elif argv[i] in ["-w", "-wait","--wait"]:
              wait = float(argv[i+1])
              del(argv[i:i+2])
          elif argv[i] in ["-b", "-bbox","--bbox"]:
              bbox = argv[i+1]
              if not BBOX_OPTION_FORMAT.match(bbox):
                command_line_error("paramètre bbox invalide: " + bbox, HELP_MESSAGE)
                return
              bbox = list(map(float,bbox.split(",")))
              del(argv[i:i+2])
          else:
              command_line_error("option invalide: " + argv[i], HELP_MESSAGE)
              return
      else:
          i = i + 1
  else:
      cadastreWebsite = command_line_open_cadastre_website(argv)
      if type(cadastreWebsite) in [str, str]:
          command_line_error(cadastreWebsite, HELP_MESSAGE)
      elif cadastreWebsite != None:
          code_departement = cadastreWebsite.code_departement
          code_commune = cadastreWebsite.code_commune
          nom_commune = cadastreWebsite.communes[code_commune]
          sys.stderr.write("Teléchargement des PDFs de la commune " + code_commune + " : " + nom_commune + "\n")
          sys.stderr.flush()
          write_string_to_file("", code_commune + "-" + nom_commune + ".txt")
          result = []
          for f in download_pdfs(cadastreWebsite, code_departement, code_commune,mode=mode,size=size,nb=nb,ratio=ratio,wait=wait,force_bbox=bbox):
              sys.stdout.write(f)
              sys.stdout.write("\n")
              sys.stdout.flush()
              result.append(f)
          return result

if __name__ == '__main__':
    cadastre_2_pdfs(sys.argv)

