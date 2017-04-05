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

Exporte un fichier osm des adresses depuis la base de donnée.

"""

import os
import re
import sys
import json
import time
import os.path
import argparse
import psycopg2
import unicodedata

try:
    import editdistance
except:
    sys.stderr.write("PLEASE INSTALL pip install editdistance")
    sys.exit(-1)

import db
from import_json import normalise_numero_departement
from import_json import normalise_numero_commune
from export_osm import normalise_numero_insee
from export_osm import commune_geometry_sql_expression
from export_osm import liste_numero_communes
from export_osm import st_geometry_to_osm_primitive
from export_osm import liste_parcelles_commune
from export_osm import sql_result_to_osm
from export_osm import SOURCE_TAG
from export_osm import OSMFile


RE_NUMERO_CADASTRE = re.compile("^([0-9]+)(( bis)|( ter)|( quater)|( quinquies)|([A-Za-z?]*))\\b", re.I)


def normalise_mot(mot):
    return unicodedata.normalize('NFD',unicode(mot)).encode("ascii","ignore").lower()

def separe_numero_du_nom_de_voie(adresse):
    num_match = RE_NUMERO_CADASTRE.match(adresse)
    if num_match:
        return adresse[:num_match.end()], adresse[num_match.end():].strip()
    else:
        return None, adresse

def decode_utf8_strip(str):
    return str.decode("utf-8").strip()

def numeros_des_adresses_parcelles_commune(numero_departement, numero_commune):
    numeros_des_adresses = dict_of(lambda: dict())
    for parcelle in liste_parcelles_commune(numero_departement, numero_commune,
            #["idu", "adresses", "ST_AsText(ST_PointOnSurface(geometry)) AS center"]):
# psycopg2.InternalError: ERREUR:  First argument geometry could not be converted to GEOS: IllegalArgumentException: Invalid number of points in LinearRing found 3 - must be 0 or >= 4
            ["idu", "adresses", "ST_AsText(ST_PointOnSurface(ST_MakeValid(geometry))) AS center"]):
            #["idu", "adresses", "ST_AsText(ST_Centroid(ST_MakeValid(geometry))) AS center"]):
        if parcelle.adresses:
            adresses = map(decode_utf8_strip, list(parcelle.adresses))
            for numero, nom_voie in map(separe_numero_du_nom_de_voie, adresses):
                if numero: numeros_des_adresses[nom_voie][numero] = parcelle.center
    return numeros_des_adresses


def distance_levenshtein_zoncommuni(nom_voie, tex_zoncommuni):
    """Dans la couche zoncommuni du cadastre, qui représente les voies
       de communication, le tex est un tableau de chaine de caractères,
       potentiellement dans le désordre.
       Pour calculer la distance de levenshtein, on regroupe et redécoupe
       tex_zoncommuni en mots, et on checher mot par mot celui
       qui correspond le mieux.
       On cherche les mots en ordre inverse de ceux du nom_voie,
       car les dernier mots du nom de rue devrait être les plus
       significatifs.
    """
    #TODO: rempalcer les abréviation de type de voie dans nom_voie,
    # car elle ne sont pas abréviée dans zoncommuni.
    tex_zoncommuni = " ".join(map(decode_utf8_strip, tex_zoncommuni))
    tex_zoncommuni = map(normalise_mot, tex_zoncommuni.split(" "))
    distance_totale = 0
    for mot in reversed(map(normalise_mot, nom_voie.split(" "))):
        if len(tex_zoncommuni):
            # Choisi le mots avec la plus petite distance de levenshtein:
            distance, match = sorted([(editdistance.eval(mot, m), m) for m in tex_zoncommuni])[0]
            distance_totale = distance_totale + distance
            tex_zoncommuni.remove(match)
        else:
            distance_totale = distance_totale + len(mot) + 1
    # Si il reste des éléments dans la liste tex_zoncommuni, ce n'set pas grave,
    # on les ignore, il y a souvent des mots en plus.
    return distance_totale


def cherche_nom_voie_la_plus_proche(geometry, nom_voies):
    """Recherche dans la table zoncommuni la voie la plus proche de
       la geometrie donnée.
       Si son nom correspond à un nom de la liste nom_voies,
       retourne la distance geophaprique et ce nom
       Sinon retourne (inf, None)
    """
    db.execute("""SELECT  tex, ST_Distance(zoncommuni.geometry::geography, point::geography) as distance
       FROM """ + db.TABLE_PREFIX + """zoncommuni AS zoncommuni,
            ST_GeomFromText(%s, 4326) AS point
       WHERE ST_DWithin(zoncommuni.geometry::geography, point::geography, 50)
       ORDER BY zoncommuni.geometry::geography <->  point::geography
       LIMIT 1""",
       [geometry])
    result = db.cur.fetchone()
    if result:
        tex_zoncommuni = result.tex
        distance_geopraphique = result.distance
        print tex_zoncommuni, distance_geopraphique
        distance_levenshtein, nom_voie = sorted([(distance_levenshtein_zoncommuni(nom_voie, tex_zoncommuni), nom_voie) for nom_voie in nom_voies])[0]
        print "distance_levenshtein", distance_levenshtein
        if float(distance_levenshtein) / float(len(nom_voie)) < 0.5:
            return distance_geopraphique, nom_voie
    return float("inf"), None


class ConfiltsVoies(object):
    """Cherche a resoudre des conflits quand
       plusieurs point numeros d'adresse identiques sont associer
       à la même parcelle, mais pour des voies différentes
    """
    def __init__(self):
        self.liste = list()
        self.liste_par_numero_et_voie = dict_of(lambda: list())

    def add(self, item):
        """Ajoute un point adresse pour lequel il y a des conflits,
           cad que le champ item.tags["addr:street"] contient une liste
           de voies possibles.
        """
        assert type(item.tags["addr:street"]) == list
        self.liste.append(item)
        numero = item.tags["addr:housenumber"]
        for voie in item.tags["addr:street"]:
            self.liste_par_numero_et_voie[(numero, voie)].append(item)

    def resoudre(self):
        """Résoud les conflits, remplace le champs item.tags["addr:street"]
           d'une liste par une valeur unique.
        """
        cas_triee_par_distance = sorted(map(
            lambda item: (cherche_nom_voie_la_plus_proche(
                            "POINT(%f %f)" % (item.lon,item.lat),
                            item.tags["addr:street"]),
                          item),
            self.liste))
        for (distance, voie), item in cas_triee_par_distance:
            if distance < 50 and voie in item.tags["addr:street"]:
                self.__resoudre_cas__(item, voie)
        for item in self.liste:
            if len(item.tags["addr:street"]) == 1:
                item.tags["addr:street"] = item.tags["addr:street"][0]
            else:
                fixme = u"choisir la bonne rue a associer: " + " ou ".join(item.tags["addr:street"])
                item.tags["addr:street"] = "|".join(item.tags["addr:street"])
                if fixme in item.tags:
                    item.tags["fixme"] = fixme + " ET " + item.tags["fixme"]
                else:
                    item.tags["fixme"] = fixme

    def __resoudre_cas__(self, item, voie):
        numero = item.tags["addr:housenumber"]
        for i in self.liste_par_numero_et_voie[(numero, voie)]:
            if voie in i.tags["addr:street"]:
                i.tags["addr:street"].remove(voie)
        item.tags["addr:street"] = [voie]


class dict_of(dict):
    """Dictionaire qui créé automatiquement (avec le constructeur donne)
       les élément demandés si il n'exisitent pas encore.
    """
    def __init__(self, constructor):
        dict.__init__(self)
        self.constructor = constructor
    def __getitem__(self, key):
        result = self.get(key)
        if result is None:
            result = self.constructor()
            self[key] = result
        return result


def export_adresses(numero_departement, numero_commune, osmfile):
    autres_adresses = numeros_des_adresses_parcelles_commune(numero_departement, numero_commune)
    db.execute("""SELECT
            tex,
            creat_date,
            update_date,
            object_rid,
            parcelle_idu,
            adresses,
            ST_AsText(numvoie_geometry) AS original,
            ST_AsText(deplace_sur_parcelle) AS deplace_sur_parcelle,
            ST_Distance_Sphere(numvoie_geometry, deplace_sur_parcelle) AS distance_parcelle,
            dans_parcelle
        FROM (
            SELECT
                numvoie.tex AS  tex,
                numvoie.creat_date AS creat_date,
                numvoie.update_date AS update_date,
                numvoie.object_rid AS object_rid,
                numvoie.parcelle_idu AS parcelle_idu,
                parcelle.adresses AS  adresses,
                numvoie.geometry AS numvoie_geometry,
                ST_Transform(
                    ST_ClosestPoint(
                        ST_Transform(ST_ExteriorRing(ST_GeometryN(parcelle.geometry, 1)), 3857),
                        ST_Transform(numvoie.geometry, 3857)),
                    4326) AS deplace_sur_parcelle,
                St_Intersects(numvoie.geometry, parcelle.geometry) AS dans_parcelle
            FROM {0}numvoie AS numvoie
            LEFT JOIN {0}parcelle AS parcelle
            ON numvoie.parcelle_idu = parcelle.idu
            WHERE numvoie.departement=%s
                AND parcelle.departement=%s
                AND ST_Intersects(numvoie.geometry, {1})
        ) AS req;""".format(
            db.TABLE_PREFIX,
            commune_geometry_sql_expression(numero_departement, numero_commune)),
        [numero_departement, numero_departement])

    conflits_voies = ConfiltsVoies()
    for tex, creat_date, update_date, object_rid, parcelle_idu, adresses, original, deplace_sur_parcelle, distance_parcelle, dans_parcelle in db.cur:
        if not parcelle_idu.startswith(numero_commune):
            continue
        numero = " ".join(tex).decode("utf-8").strip()
        num_parcelle = str(int(parcelle_idu[-4:]))
        fixme= []
        nom_voies = []
        if numero and adresses:
            adresses = map(decode_utf8_strip, adresses)
            for adr_numero, nom_voie in map(separe_numero_du_nom_de_voie, adresses):
                if adr_numero == numero:
                    if numero in autres_adresses[nom_voie]:
                        del(autres_adresses[nom_voie][numero])
                    nom_voies.append(nom_voie)
        geometry = deplace_sur_parcelle if ( \
                ((distance_parcelle < 4) and (not dans_parcelle)) \
                or (dans_parcelle and distance_parcelle < 0.5)) \
            else original
        item = st_geometry_to_osm_primitive(geometry, osmfile)
        item.tags["source:date"] = str(update_date)
        item.tags["source"] = SOURCE_TAG
        item.tags["ref:FR:cadastre"] = numero_departement + ":" + str(object_rid)
        item.tags["addr:housenumber"] = numero
        if len(nom_voies) == 1:
            item.tags["addr:street"] = nom_voies[0]
        elif len(nom_voies) > 1:
            item.tags["addr:street"] = nom_voies
            conflits_voies.add(item)
        else:
            fixme.append(u"associer à la bonne rue, numéro en théorie lié à la parcelle n°" + num_parcelle + u" situé à " + str(int(distance_parcelle)) + " m")
        if (distance_parcelle > 10) and (not dans_parcelle):
            fixme.append(str(int(distance_parcelle)) + u" m de la parcelle n°" + num_parcelle + u": vérifier la position")
            fixme.reverse()
        if fixme: item.tags["fixme"] = " et ".join(fixme)
    conflits_voies.resoudre()
    for nom_voie, numeros in autres_adresses.items():
        # Adresses des parcelles qui n'ont pas trouvé de numéro
        for numero, geometry in numeros.items():
            item = st_geometry_to_osm_primitive(geometry, osmfile)
            item.tags["source"] = SOURCE_TAG
            item.tags["addr:housenumber"] = numero
            item.tags["addr:street"] = nom_voie
    corrige_addr_street(numero_departement, numero_commune, osmfile)
    export_numeros_orphelins(numero_departement, numero_commune, osmfile)


def corrige_addr_street(numero_departement, numero_commune, osmfile):
    # TODO
    pass

def export_numeros_orphelins(numero_departement, numero_commune, osmfile):
    """Exporte les numeros n'ayant pas de parcelle associée, donc dont on
       n'as pas le nom de la voie"""
    db.execute("""SELECT ST_AsText(numvoie.geometry) AS geometry, numvoie.update_date, numvoie.object_rid, numvoie.tex
            FROM {0}numvoie AS numvoie
            LEFT JOIN {0}parcelle AS parcelle
            ON numvoie.parcelle_idu = parcelle.idu
            WHERE numvoie.departement=%s
                AND parcelle.idu=null
                AND ST_Intersects(numvoie.geometry, {1})
        """.format(
            db.TABLE_PREFIX,
            commune_geometry_sql_expression(numero_departement, numero_commune)),
        [numero_departement])
    for result in db.cur:
        item = sql_result_to_osm(result, numero_departement, osmfile)
        item.tags["addr:housenumber"] = item.tags["name"]
        item.tags["fixme"] = u"associer à la bonne rue"
        del(item.tags["name"])

def export_osm_adresses(departement, commune):
    departement  = normalise_numero_departement(departement)
    commune = normalise_numero_commune(commune)
    numero_insee = normalise_numero_insee(departement, commune)
    prefix = numero_insee  + "-"

    osmfile = OSMFile()
    export_adresses(departement, commune, osmfile)
    osmfile.write_if_not_empty(prefix + "adresse.osm")


def main(args):
    parser = argparse.ArgumentParser(description="Export des adresses d'une commune au format .osm")
    parser.add_argument("departement", help="code departement", type=str)
    parser.add_argument("commune", help="code commune", type=str)
    args = parser.parse_args(args)

    if (args.commune.lower() in ["all", "toutes"]):
        for commune in liste_numero_communes(args.departement):
            export_osm_adresses(args.departement, commune)
    else:
        export_osm_adresses(args.departement, args.commune)


if __name__ == '__main__':
    main(sys.argv[1:])

