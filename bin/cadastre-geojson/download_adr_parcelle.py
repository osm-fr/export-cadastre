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

Télécharche depuis le site web du cadastre les adresse associées aux parcelles
d'une commune, et met a jour la base de donéne.

"""

import re
import sys
import json
import time
import os.path
import datetime
import argparse

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),"cadastre-housenumber"))

import db
from import_json import normalise_numero_commune
from import_json import normalise_numero_departement
from cadastre_fr.website import CadastreWebsite
from cadastre_fr.parcel import iter_download_parcels_info_pdf
from cadastre_fr.parcel import parse_addresses_of_parcels_info_pdfs
from cadastre_fr.tools import iteritems
from export_osm import commune_geometry_sql_expression
from export_osm import liste_parcelles_commune
from export_osm import liste_numero_communes


def ouvre_cadastre_website_commune(numero_departement, numero_commune):
    cadastreWebsite = CadastreWebsite()
    cadastreWebsite.set_departement(numero_departement)
    code_commune = [key for key in cadastreWebsite.get_communes().keys() if key.endswith(numero_commune)]
    if len(code_commune) == 1:
        code_commune = code_commune[0]
    elif len(code_commune) == 0:
        raise Exception("Commune " + numero_commune + " non trouvée sur cadastre.gouv.fr")
    else:
        raise Exception("Plusieurs codes pour la commune: " + ", ".join(code_commune))
    cadastreWebsite.set_commune(code_commune)
    return cadastreWebsite, code_commune


def telecharge_adresses_parcelles(numero_departement, numero_commune):
    numero_departement = normalise_numero_departement(numero_departement)
    numero_commune = normalise_numero_commune(numero_commune)
    cadastreWebsite, code_commune  = ouvre_cadastre_website_commune(numero_departement, numero_commune)
    # Le site web du cadastre utilise 2 lettres bizare en entête des
    # numeros de commune et des numéros de parcelles:
    id_parcelles = sorted(set([code_commune[0:2] + parcelle.idu for parcelle in
        liste_parcelles_commune(numero_departement, numero_commune, ["idu"])]))
    info_pdfs = iter_download_parcels_info_pdf(cadastreWebsite, id_parcelles)
    id_trouves = set()
    for id_parcelle, adresses in iteritems(parse_addresses_of_parcels_info_pdfs(info_pdfs, code_commune)):
        id_trouves .add(id_parcelle)
        idu = id_parcelle[2:]
        db.execute("UPDATE " + db.TABLE_PREFIX + "parcelle SET adresses = %s WHERE departement=%s AND idu=%s""",
                   (adresses, numero_departement, idu))
        if db.cur.rowcount != 1:
            sys.stderr.write("ERREUR: {0} lignes mise à jour la parcelle {1}, adressse={2}\n".format(str(db.cur.rowcount), idu, adresses))
        db.db.commit()
    if len(id_trouves) < len(id_parcelles):
        sys.stderr.write("ERREUR: adresses non trouvées pour les parcelles " + str(sorted(set(id_parcelles) - id_trouves)))

def main(args):
    parser = argparse.ArgumentParser(description="Télécharge depuis cadastre.gouv.fr les adresses des parcelles d'une commune, met à jour la base de donnée.")
    parser.add_argument("departement", help="numéro departement", type=str)
    parser.add_argument("commune", help='numéro commune, "toutes" = toutes les communes', type=str)
    args = parser.parse_args(args)
    if (args.commune.lower() in ["all", "toutes"]):
        for numero_commune in liste_numero_communes(args.departement):
            telecharge_adresses_parcelles(args.departement, numero_commune)
    else:
        telecharge_adresses_parcelles(args.departement, args.commune)

if __name__ == '__main__':
    main(sys.argv[1:])

