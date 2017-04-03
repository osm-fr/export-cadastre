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

def liste_numero_commune(numero_departement):
    numero_departement = normalise_numero_departement(numero_departement)
    db.execute("SELECT idu FROM " + db.TABLE_PREFIX + "commune WHERE departement=%s", [numero_departement])
    return [normalise_numero_commune(result[0]) for result in db.cur]

def telechare_adresses_parcelles(numero_departement, numero_commune):
    numero_departement = normalise_numero_departement(numero_departement)
    numero_commune = normalise_numero_commune(numero_commune)
    cadastreWebsite= CadastreWebsite()
    cadastreWebsite.set_departement(numero_departement)
    code_commune = [key for key in cadastreWebsite.get_communes().keys() if key.endswith(numero_commune)]
    if len(code_commune):
        code_commune = code_commune[0]
    else:
        raise Exception("Commune " + numero_commune + " non trouvée")
    cadastreWebsite.set_commune(code_commune)
    db.execute("SELECT idu FROM " + db.TABLE_PREFIX + "parcelle WHERE ST_Intersects(geometry, {})".format(
        commune_geometry_sql_expression(numero_departement, numero_commune)))
    parcelles_ids = [code_commune[0:2] + result[0] for result in db.cur]
    result_ids = set()
    info_pdfs = iter_download_parcels_info_pdf(cadastreWebsite, parcelles_ids)
    for parcelle_id, adresses in iteritems(parse_addresses_of_parcels_info_pdfs(info_pdfs, code_commune)):
        result_ids.add(parcelle_id)
        idu = parcelle_id[2:]
        db.execute("UPDATE " + db.TABLE_PREFIX + "parcelle SET adresses = %s WHERE departement=%s AND idu=%s""",
                   (adresses, numero_departement, idu))
        if db.cur.rowcount != 1:
            # FIXME: que faire des ces adresses de parcelles qu'on ne connait
            # pas (et qu'on a donc pas demandé...) ?
            sys.stderr.write("ERROR: {0} row updated for parcelle {1}, adressse={2}\n".format(str(db.cur.rowcount), idu, adresses))
        db.db.commit()
    parcelles_ids = set(parcelles_ids)
    pas_trouve = parcelles_ids - result_ids
    pas_demande = result_ids - parcelles_ids
    print "NB DEMANDÉS:", len(parcelles_ids)
    print "NB RESULTAS:", len(result_ids)
    print "PAS TROUVÉ:", len(pas_trouve), sorted(pas_trouve)
    print "PAS DEMANDÉ:", len(pas_demande), sorted(pas_demande)


def main(args):
    parser = argparse.ArgumentParser(description="Télécharge depuis cadastre.gouv.fr les adresses des parcelles d'une commune, met à jour la base de donnée.")
    parser.add_argument("departement", help="numéro departement", type=str)
    parser.add_argument("commune", help='numéro commune, "toutes" = toutes les communes', type=str)
    args = parser.parse_args(args)
    if (args.commune.lower() in ["all", "toutes"]):
        for numero_commune in liste_numero_commune(args.departement):
            telechare_adresses_parcelles(args.departement, numero_commune)
    else:
        telechare_adresses_parcelles(args.departement, args.commune)

if __name__ == '__main__':
    main(sys.argv[1:])

