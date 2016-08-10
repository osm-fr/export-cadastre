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
Vérifie que toutes les villes sont présente
dans le fichier associatedStreet/osm_id_ref_insee.csv
"""

import os
import sys
import os.path
from glob import glob

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.website import code_insee

insee_set = set()
for line in open("associatedStreet/osm_id_ref_insee.csv"):
  insee=line.strip().split(",")[1]
  insee_set.add(insee)

for f in glob("/data/work/cadastre.openstreetmap.fr/data/*/*.txt"):
  for line in open(f):
    items = line.split()
    dep,com = items[:2]
    name = " ".join(items[2:])
    insee = code_insee(dep,com)
    if not insee in insee_set:
        print "ERREUR: id area manquant pour le code insee %s (%s)" % (insee, name)
