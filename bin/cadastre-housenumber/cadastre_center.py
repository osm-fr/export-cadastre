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
Récupération du centre du cadastre d'une commune.

"""

import sys

from cadastre import CadastreWebsite
from cadastre import command_line_open_cadastre
from pdf_vers_osm_housenumbers import CadastreToOSMTransform


def print_help():
    programme = sys.argv[0]
    spaces = " " * len(programme)
    sys.stdout.write((u"Récupération du centre du cadastre d'une commune" + "\n").encode("utf-8"))
    sys.stdout.write((u"USAGE:" + "\n").encode("utf-8"))
    sys.stdout.write((u"%s  DEPARTEMENT COMMUNE" % programme + "\n").encode("utf-8"))
    sys.stdout.write((u"           récupère le centre du cadastre d'une commune.\n").encode("utf-8"))
    sys.stdout.write((u"%s  " % programme + "\n").encode("utf-8"))
    sys.stdout.write((u"           liste les départements" + "\n").encode("utf-8"))
    sys.stdout.write((u"%s  DEPARTEMENT" % programme + "\n").encode("utf-8"))
    sys.stdout.write((u"           liste les communes d'un département" + "\n").encode("utf-8"))

def command_line_error(message, help=False):
    sys.stdout.write(("ERREUR: " + message + "\n").encode("utf-8"))
    if help: print_help()

def getCenter(cadastreWebsite):
    projection = cadastreWebsite.get_projection()
    x1,y1,x2,y2 = cadastreWebsite.get_bbox()
    x = (x1+x2)/2
    y = (y1+y2)/2
    return CadastreToOSMTransform(projection).transform_point((x,y))
  

def cadastre_center(argv):
  if len(argv) == 1: 
      command_line_open_cadastre(argv)
  elif len(argv) == 2: 
      error = command_line_open_cadastre(argv)
      if error: command_line_error(error)
  elif len(argv) > 3: 
      command_line_error(u"trop d'arguments")
  else:
      cadastreWebsite = command_line_open_cadastre(argv)
      if type(cadastreWebsite) in [str, unicode]:
          command_line_error(cadastreWebsite, help=False)
      else:
        lon,lat = getCenter(cadastreWebsite)
        print("%f,%f" % (lat, lon))

if __name__ == '__main__':
    cadastre_center(sys.argv)

