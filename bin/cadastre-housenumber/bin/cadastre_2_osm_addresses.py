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
Tentative de merge des infos d'adresse du cadastre:
 - celles venant des export PDF: localisation de numéros de rue
 - celles venant des info des parcelles

ATTENTION: l'utilisation des données du cadastre n'est pas libre, et ce script doit
donc être utilisé exclusivement pour contribuer à OpenStreetMap, voire 
http://wiki.openstreetmap.org/wiki/Cadastre_Fran%C3%A7ais/Conditions_d%27utilisation

"""

import sys
import os.path
import urllib2

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.tools    import command_line_error
from cadastre_fr.tools    import write_string_to_file
from cadastre_fr.website  import CadastreWebsite
from cadastre_fr.website  import command_line_open_cadastre_website
from cadastre_fr.address  import cadastre_2_osm_addresses

HELP_MESSAGE = u"""Récupération des adresses depuis le cadaste
USAGE:
{0}  [-data] [-nd] [-nobis] CODE_DEPARTEMENT CODE_COMUNE
OPTIONS:
    -data : n'extrait que les données brutes
    -nd : ne retélécharge pas, utilise les fichiers déja présents
    -nobis : ne transforme pas B,T,Q en bis, ter, quater et n'ajoute pas d'espace.
    -ne : ne pas utiliser de données externes (FANTOIR et OSM).
    -nzip : ne pas découper le résultat par rue et en faire des zip.""".format(sys.argv[0])


def main(argv):
  download = True
  merge_addresses = True
  bis = True
  use_external_data = True
  split_result = True
  i = 1
  while i < len(argv):
      if argv[i].startswith("-"):
          if argv[i] in ["-h", "-help","--help"]:
              command_line_error(None, HELP_MESSAGE)
          elif argv[i] in ["-nobis"]:
              bis = False
              del(argv[i:i+1])
          elif argv[i] in ["-nd", "-nodownload"]:
              download = False
              del(argv[i:i+1])
          elif argv[i] in ["-data"]:
              merge_addresses = False
              del(argv[i:i+1])
          elif argv[i] in ["-ne"]:
              use_external_data = False
              del(argv[i:i+1])
          elif argv[i] in ["-nzip"]:
              split_result = False
              del(argv[i:i+1])
          else:
              command_line_error(u"option invalide: " + argv[i], HELP_MESSAGE)
              return
      else:
          i = i + 1
  if len(argv) <= 1:
      command_line_open_cadastre_website(argv)
      return
  elif len(argv) == 2:
      error = command_line_open_cadastre_website(argv)
      if error: command_line_error(error, HELP_MESSAGE)
  elif len(argv) > 3:
      command_line_error(u"trop d'arguments", HELP_MESSAGE)
  else:
      try:
          cadastreWebsite = command_line_open_cadastre_website(argv)
          if type(cadastreWebsite) in [str, unicode]:
              command_line_error(cadastreWebsite)
              return
          else:
              code_departement = cadastreWebsite.code_departement
              code_commune = cadastreWebsite.code_commune
              nom_commune = cadastreWebsite.communes[code_commune]
              write_string_to_file("", code_commune + "-" + nom_commune + ".txt")
      except urllib2.URLError:
          if download:
              command_line_error(u"problème de connexion au site du cadastre", HELP_MESSAGE)
              return
          else:
              sys.stdout.write(u"problème de connexion au site du cadastre\n".encode("utf-8"));
              code_departement = argv[1]
              code_commune = argv[2]
              nom_commune = "inconnu"
      cadastre_2_osm_addresses(cadastreWebsite, code_departement, code_commune,  nom_commune, download, bis, merge_addresses, use_external_data, split_result)


if __name__ == '__main__':
    main(sys.argv)


