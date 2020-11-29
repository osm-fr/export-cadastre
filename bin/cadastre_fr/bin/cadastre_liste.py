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
Liste les départements et les communes du cadastre
(https://cadastre.gouv.fr)
"""

import re
import sys
import time
import os.path

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from cadastre_fr.tools import command_line_error
from cadastre_fr.website import CadastreWebsite
from cadastre_fr.download_pdf import PDF_DOWNALOD_WAIT_SECONDS

postal_code_suffix = re.compile(".* \([0-9A-Z]{5}\)$")

def cadastre_liste_dep_com(argv):
    cadastreWebsite = CadastreWebsite()
    departements = cadastreWebsite.get_departements()
    if len(departements) > 0:
        with open("dep-liste.txt","w") as dep_file:
            for dep_code,dep_name in departements.items():
                dep_file.write('{} "{}"\n'.format(dep_code, dep_name))
        count = 0;
        for dep_code,dep_name in departements.items():
            count = count + 1
            if (count % 10) == 0:
                time.sleep(PDF_DOWNALOD_WAIT_SECONDS)
            print(dep_code, dep_name)
            if not os.path.exists(dep_code):
                os.mkdir(dep_code)
            cadastreWebsite.set_departement(dep_code)
            communes = cadastreWebsite.get_communes()
            if len(communes) > 0:
                with open("{}/{}-liste.txt".format(dep_code, dep_code, dep_code), "w") as com_file:
                    for com_code, com_name in communes.items():
                        if postal_code_suffix.match(com_name):
                            com_name = com_name[:-8]
                        #print(dep_code, com_code, com_name)
                        com_file.write('{} {} "{}"\n'.format(dep_code, com_code, com_name))
            else:
                print("ERREUR: aucune commune trouvée pour le département", dep_code)
    else:
        print("ERREUR: aucun département trouvé")
        sys.exit(-1)

if __name__ == '__main__':
    cadastre_liste_dep_com(sys.argv)

