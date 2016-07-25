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

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from cadastre_fr.website    import CadastreWebsite
from cadastre_fr.website    import command_line_open_cadastre_website
from cadastre_fr.transform  import CadastreToOSMTransform
from cadastre_fr.tools      import command_line_error



def getCenter(cadastreWebsite):
    projection = cadastreWebsite.get_projection()
    x1,y1,x2,y2 = cadastreWebsite.get_bbox()
    x = (x1+x2)/2
    y = (y1+y2)/2
    return CadastreToOSMTransform(projection).transform_point((x,y))
  

HELP_MESSAGE = u""""Récupération du centre du cadastre d'une commune
USAGE:
{0}  DEPARTEMENT COMMUNE
    récupère le centre du cadastre d'une commune.
{0}
    liste les départements
{0}  DEPARTEMENT
    liste les communes d'un département""".format(sys.argv[0], " " * len(sys.argv[0]))


def cadastre_center(argv):
  if ("-h" in argv) or ("-.help" in argv):
      print(HELP_MESSAGE)
  else:
      cadastre = command_line_open_cadastre_website(argv)
      if type(cadastre) in (str,unicode):
        command_line_error(website, HELP_MESSAGE)
      elif cadastre != None:
        lon,lat = getCenter(cadastre)
        print("%f,%f" % (lat, lon))

if __name__ == '__main__':
    cadastre_center(sys.argv)

