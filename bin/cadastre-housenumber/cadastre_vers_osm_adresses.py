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

import re
import sys
import os.path
import time
import subprocess
import json
import glob
import operator
import rtree.index
import urllib2
import zipfile
import xml.etree.ElementTree as ET
from itertools import imap
from cStringIO import StringIO
from shapely.geometry import Point # pip install Shapely --upgrade
from shapely.geometry import MultiPoint
from shapely.geometry.polygon import Polygon
from shapely.geometry.multipolygon import MultiPolygon
import math
import shapely.geometry
import shapely.prepared
import traceback

from osm import Osm,Node,Way,OsmWriter,Relation
from cadastre import CadastreWebsite
from cadastre import command_line_open_cadastre
from cadastre import code_insee
from mytools import write_string_to_file
from mytools import write_stream_to_file
from mytools import to_ascii
from cadastre_vers_pdf import iter_download_pdfs
#from pdf_vers_svg import pdfs_vers_svgs
from pdf_vers_osm_housenumbers import BoundingBox
from pdf_vers_osm_housenumbers import CadastreParser
from pdf_vers_osm_housenumbers import HousenumberPathRecognizer
from pdf_vers_osm_housenumbers import CadastreToOSMTransform
from pdf_vers_osm_noms import NamePathRecognizer
from pdf_vers_osm_limites_parcelles import ParcellePathRecognizer
from partitionnement_noeuds_osm import partitionnement_osm_nodes
#from fantoir import get_mapping_nom_fantoir_vers_osm
import addrfantoir

import bbox_vers_osm_box

ATTENTE_EN_SECONDE_ENTRE_DOWNLOAD = 2
# Nombre max de parcelles pour par requette bbox:
MAX_PARCELLES_PAR_BBOX = 1500
# Nombre max de parcelles pour lesquelles on demande les info en une fois:
MAX_PARCELLES_PAR_INFO_PDF = 100

# Taille du partitionnemens des noeus addr:housenumber qui sont orphelins
# (sans rue connue) ou ambigus (plus d'une rue possible)
TAILLE_PARTITIONEMENT_NOEUDS = 20

PARCELLE_LIMITE_MATCH_BOUNDS_TOLERANCE = 1  # expressed in cadastre reference ~= meter
PARCELLE_LIMITE_MATCH_AREA_TOLERANCE   = 10 # expressed in cadastre reference ~= square meter
NUMERO_RE =  re.compile("^[0-9][0-9A-Za-z]*(( bis)|( ter)|( quater)|)")

SOURCE_TAG = u"cadastre-dgi-fr source : Direction Générale des Impôts - Cadastre. Mise à jour : " + time.strftime("%Y")

def print_help():
    programme = sys.argv[0]
    spaces = " " * len(programme)
    sys.stdout.write((u"Récupération des adresses depuis le cadaste\n").encode("utf-8"))
    sys.stdout.write((u"USAGE:" + "\n").encode("utf-8"))
    sys.stdout.write((u"%s  [-data] [-nd] CODE_DEPARTEMENT CODE_COMUNE" % programme + "\n").encode("utf-8"))
    sys.stdout.write((u"OPTIONS:" + "\n").encode("utf-8"))
    sys.stdout.write((u"    -data : n'extrait que les données brutes\n").encode("utf-8"))
    sys.stdout.write((u"    -nd : ne retélécharge pas, utilise les fichiers déja présents\n").encode("utf-8"))

def command_line_error(message, help=False):
    sys.stdout.write(("ERREUR: " + message + "\n").encode("utf-8"))
    if help: print_help()


class Parcelle(object):
    def __init__(self, fid, nature="", libellex=0.0, libelley=0.0,
            xmin=0.0,ymin=0,xmax=0.0,ymax=0.0,surface_geom=0.0,
            limite=None):
        self.__dict__.update(locals()); del self.self
        self.bounds = (self.xmin, self.ymin, self.xmax, self.ymax)
        self.area = surface_geom
        self.box = shapely.geometry.box(*self.bounds)

    @staticmethod
    def parse_xml_strings(xmls):
      """parse le résultat xml d'une liste de parcelles du cadastre"""
      # utilise une table de hachage pour suprimier le éléments redondants:
      resultmap = {}
      for xml in xmls:
          #tree = ET.parse(filename).getroot()
          tree = ET.fromstring(xml)
          for parcelle in tree:
              param = {attr : float(parcelle.iter(attr.upper()).next().text) for attr in
                  ["libellex", "libelley", "xmin","xmax","ymin","ymax","surface_geom"]}
              fid  = parcelle.attrib['fid'][9:]
              resultmap[fid] = Parcelle(
                  fid  = parcelle.attrib['fid'][9:],
                  nature = parcelle.iter("NATURE").next().text,
                  **param)
      return resultmap




def parse_adresses_of_parcelles_info_pdfs(pdfs, code_commune):
    """parse le pdf d'info des parcelles du cadastre,
       retourne une table de hachage entre l'id des parcelles
       et une liste d'adresses"""
    adresses_parcelles = {}
    code_postal_re =  re.compile("(.*)^[0-9]{5}.*", re.S|re.M)
    for filename in pdfs:
        txt = subprocess.check_output(["pdftotext", filename, "-"])
        mode_adresse = False
        for line in txt.splitlines():
            line = line.strip()
            if line.startswith("Service de la Documentation Nationale du Cadastre") \
                    or line.startswith("82, rue du Maréchal Lyautey - 78103 Saint-Germain-en-Laye Cedex") \
                    or line.startswith("SIRET 16000001400011") \
                    or line.startswith("©2012 Ministère de l'Économie et des Finances") \
                    or line.startswith("Informations sur la feuille éditée par internet le "):
                continue
            #print line
            if line.startswith("Références de la parcelle "):
                id1,id2,id3 = line[len("Références de la parcelle "):].strip().split(" ")
                if len(id2) ==1:
                   id2 = "0" + id2
                id3 = "%04d" % int(id3)
                id_parcelle = str(code_commune + id1 + id2 + id3)
                adresses = []
                adresses_parcelles[id_parcelle] = adresses
                mode_adresse = False
            elif line == "Adresse":
                adresses.append("")
                mode_adresse = True
            elif mode_adresse and len(line) > 0:
                if len(adresses[-1]) == 0:
                    adresses[-1] = line
                else:
                    adresses[-1] = adresses[-1] + '\n' + line

    # Supprimme la fin de l'adresse à partir du code postal
    # et remplace les retours à la ligne par un espace:
    # Enlève aussi les doublons avec un set(), car si une parcelle 
    # a deux fois exactement la même adresse, cela vas faire planter l'algo 
    # de la fonction match_parcelles_et_numeros
    # comme par exemple à Beauvais (département 60 code commune O0057)
    for id_parcelle, adresses in adresses_parcelles.iteritems():
        set_adresses = set()
        for adresse in adresses:
            match_code_postal = code_postal_re.match(adresse)
            if match_code_postal:
                adresse = match_code_postal.group(1)
            adresse = adresse.replace("\n"," ").strip()
            set_adresses.add(adresse)
        adresses_parcelles[id_parcelle] = list(set_adresses)

    return adresses_parcelles
  
def bounds_diff(bounds1, bounds2):
    return max([abs(operator.sub(*t)) for t in zip(bounds1, bounds2)])


def polygones_et_index_des_limite_parcelles(limite_parcelles):
    # Transforme les limites en polygones:
    polygones = []
    for linear_rings in limite_parcelles:
        polygones.append(Polygon(linear_rings[0], linear_rings[1:]))
        # Si nous avons un polygone creux, nous ajoutons ses polygones
        # interieurs a la liste des limites:
        for linear_ring in linear_rings[1:]:
            polygones.append(Polygon(linear_ring))
    # Génre un index:
    index = rtree.index.Index()
    for i,p in enumerate(polygones):
        index.insert(i, p.bounds)
    return polygones, index


def match_parcelles_et_limites(parcelles, limites, limites_index):
    """Affecte le champs .limite de chaque parcelles avec celle
    parmis la liste des limites données qui correspond, en 
    comparant la bounding box (.bounds) et à l'area (.area) 
    """
    #max_diff_bounds = 0
    #max_diff_area = 0
    for parcelle in parcelles.itervalues():
        best_diff = float("inf")
        best_limite = None
        for i in limites_index.intersection(parcelle.bounds):
            limite = limites[i]
            if abs(parcelle.area - limite.area) < PARCELLE_LIMITE_MATCH_AREA_TOLERANCE:
                diff = bounds_diff(parcelle.bounds, limite.bounds)
                if diff < best_diff:
                    best_diff = diff
                    best_limite = limite
        if best_limite and \
                best_diff < PARCELLE_LIMITE_MATCH_BOUNDS_TOLERANCE:
                #and abs(parcelle.area-best_limite.area) < PARCELLE_LIMITE_MATCH_AREA_TOLERANCE:
            parcelle.limite = best_limite
            #max_diff_bounds = max(max_diff_bounds, best_diff)
            #max_diff_area = max(max_diff_area, abs(parcelle.area - best_limite.area))
        else:
            sys.stdout.write((u"ATTENTION: limites non trouvée pour la parcelle " + parcelle.fid + "\n").encode("utf-8"))
    #print "---"          
    #print "max diff parcelles bounds: " + str(max_diff_bounds)
    #print "max diff parcelles area: " + str(max_diff_area)
    #transform = CadastreToOSMTransform(projection).transform_point
    #osm = Osm({})
    #for i in range(len(limites)):
    #    limite = limites[i]
    #    if limite:
    #        way = osm_add_polygon(osm, limite, transform)
    #        way.tags["bounds"] = str(limite.bounds)
    #        way.tags["area"] = str(limite.area)
    #        way.tags["index"] = str(i)
    #for parcelle in parcelles.itervalues():
    #    if not parcelle.ok:
    #        way = osm_add_polygon(osm, parcelle.limite, transform)
    #        way.tags["bounds"] = str(parcelle.bounds)
    #        way.tags["area"] = str(parcelle.area)
    #        way.tags["name"] = parcelle.fid
    #OsmWriter(osm).write_to_file("l.osm")
  
def match_parcelles_et_numeros(parcelles, numeros):
    numeros_index = rtree.index.Index()
    sys.stdout.write((str(len(numeros)) + u" numéros à trouver\n").encode("utf-8"))
    # Convertit les positions des numéros en Point et insere les dans l'index:
    for i,(num, position, angle) in enumerate(numeros):
        position = Point(tuple(position))
        numeros[i] = num, position, angle
        numeros_index.insert(i, position.coords[0])
    # Cherche la liste des numeros contenus dans les adresses de la parcelle:
    parcelles_des_adresses = {}
    for parcelle in parcelles.itervalues():

        # Liste d'adresses de la parcelle, indexé par leur numéro:
        parcelle.addrs_numeros = {}

        # Liste de position des numéros des adresse. Pour un numéro donné
        # on cherchera autant de position que la parcelle a d'adresse avec ce numéro
        parcelle.positions_numeros = {}
        parcelle.num_to_find = 0
        if not hasattr(parcelle, 'adresses'):
            parcelle.adresses = []
        else:
            for addr in parcelle.adresses:
                if not parcelles_des_adresses.has_key(addr):
                    parcelles_des_adresses[addr] = []
                parcelles_des_adresses[addr].append(parcelle)
                numero_match = NUMERO_RE.match(addr)
                if numero_match:
                    numero = numero_match.group(0)
                    if not parcelle.positions_numeros.has_key(numero):
                        parcelle.positions_numeros[numero] = []
                        parcelle.addrs_numeros[numero] = []
                    parcelle.addrs_numeros[numero].append(addr)
                    parcelle.num_to_find += 1
    for distance in [0,1,2,3] + range(4,50,2) + range(50,200,5):
        nb_trouve_avec_limite = 0
        nb_trouve_avec_bbox = 0
        # cherche la position des numeros contenus ou à proximité des parcelles
        for parcelle in parcelles.itervalues():
            if parcelle.num_to_find > 0:
                if hasattr(parcelle, 'limite') and parcelle.limite != None:
                    if distance == 0:
                        #print "choix parcelle.limite"
                        limite_etendue = parcelle.limite
                    else:
                        #print "choix parcelle.limite.buffer"
                        limite_etendue = parcelle.limite.buffer(distance)
                elif distance == 50:
                    # On ne connait pas les limites de la parcelle, ont utilise
                    # sa bounding box - 50m par sécurité:
                    #print "choix parcelle.box"
                    limite_etendue = parcelle.box
                elif distance > 50:
                    #print "choix parcelle.box.buffer"
                    limite_etendue = parcelle.box.buffer(distance-50)
                else:
                    limite_etendue = None
                if limite_etendue != None:
                    #print "Limite de la parcelle " + parcelle.fid + " etendue de " + str(distance)
                    #print limite_etendue
                    #print "exterior: " + str(limite_etendue.exterior.coords[:])
                    #for i in limite_etendue.interiors:
                    #    print "interiors: " + str(i.coords[:])
                    #print "bounds: " + str(limite_etendue.bounds)
                    for i in numeros_index.intersection(limite_etendue.bounds):
                        if numeros[i]:
                            num, position, _ = numeros[i]
                            if position.within(limite_etendue):
                                if parcelle.positions_numeros.has_key(num) and \
                                        (len(parcelle.positions_numeros[num]) < len(parcelle.addrs_numeros[num])):
                                        # on a vérifie qu'il faut encore trouver ce numéro pour une des adresses
                                        # de cette parcelle:
                                    parcelle.positions_numeros[num].append(position)
                                    parcelle.num_to_find -= 1
                                    # marque le numéro comme trouvé et enlève le de l'index:
                                    numeros[i] = None
                                    numeros_index.delete(i, position.coords[0])
                                    if hasattr(parcelle,'limite'):
                                        nb_trouve_avec_limite += 1
                                    else:
                                        nb_trouve_avec_bbox += 1
                                    # On parcourt la liste des parcelles qui cherchaient la même adresse
                                    # pour leur dire que c'est foutu pour elle, c'est nous qui s'approprions le numéro !
                                    addr = parcelle.addrs_numeros[num][len(parcelle.positions_numeros[num])-1]
                                    for p in parcelles_des_adresses[addr]:
                                        if p != parcelle:
                                            p.adresses.remove(addr)
                                            p.addrs_numeros[num].remove(addr)
                                            if len(p.addrs_numeros[num]) == 0:
                                                del(p.addrs_numeros[num])
                                                del(p.positions_numeros[num])
                                            p.num_to_find -= 1

        if nb_trouve_avec_limite>0:
            sys.stdout.write((str(nb_trouve_avec_limite) + u" numéros trouvés à moins de " + str(distance) + "m des limite des parcelles\n").encode("utf-8"))
        if nb_trouve_avec_bbox>0:
            sys.stdout.write((str(nb_trouve_avec_bbox) + u" numéros trouvés à moins de " + str(distance-50) + "m des bbox des parcelles\n").encode("utf-8"))
        sys.stdout.flush()
    nb_numeros_non_attache = 0
    for n in numeros:
        if n:
            nb_numeros_non_attache +=1
    if nb_numeros_non_attache == 1:
        sys.stdout.write(("ATTENTION: " + str(nb_numeros_non_attache) + u" numéro non rataché à son adresse !\n").encode("utf-8"))
    elif nb_numeros_non_attache > 1:
        sys.stdout.write(("ATTENTION: " + str(nb_numeros_non_attache) + u" numéros non ratachés à leur adresse !\n").encode("utf-8"))
    else:
        sys.stdout.write((u"Tous les numéros ont trouvé une parcelle !\n").encode("utf-8"))
    count_not_found = 0
    for parcelle in parcelles.itervalues():
      count_not_found += parcelle.num_to_find
    if count_not_found == 1:
        sys.stdout.write(("ATTENTION: " + str(count_not_found) + u" adresse n'a pas trouvé son numéro !\n").encode("utf-8"))
    elif count_not_found > 1:
        sys.stdout.write(("ATTENTION: " + str(count_not_found) + u" adresses n'ont pas trouvé leur numéro !\n").encode("utf-8"))
    else:
        sys.stdout.write((u"Toutes les adresses ont trouvé leur numéro!\n").encode("utf-8"))
    sys.stdout.flush()

def generate_osm_housenumbers(numeros, transform):
    osm = Osm({'upload':'false'})
    for numero, position, angle in numeros:
        node = osm_add_point(osm, position, transform)
        node.tags['fixme'] = u"à vérifier et associer à la bonne rue"
        node.tags['addr:housenumber'] = numero
        node.tags['source'] = SOURCE_TAG
        node.tags['angle'] = str(int(round(angle * 180 / math.pi))) + u"°"
    return osm

def generate_osm_noms(quartiers, rues, transform):
    osm = Osm({'upload':'false'})
    for nom, position, angle in quartiers:
        node = osm_add_point(osm, position, transform)
        node.tags['name'] = nom
        node.tags['place'] = 'neighbourhood'
        node.tags['source'] = SOURCE_TAG
    for nom, position, angle in rues:
        node = osm_add_point(osm, position, transform)
        node.tags['name'] = nom
        node.tags['angle'] = str(int(round(angle * 180 / math.pi))) + u"°"
        node.tags['source'] = SOURCE_TAG
    return osm

def generate_osm_parcelles(parcelles, transform):
    osm = Osm({'upload':'false'})
    for parcelle in parcelles.itervalues():
        if hasattr(parcelle,"limite") and parcelle.limite != None:
            limite = parcelle.limite
        else:
            limite = parcelle.box
        way = osm_add_polygon(osm, limite, transform)
        if hasattr(parcelle, 'adresses'):
            for i,addr in enumerate(parcelle.adresses):
                numero_match = NUMERO_RE.match(addr)
                if numero_match:
                    num = numero_match.group(0)
                    way.tags['addr%d:housenumber' % i] = num
                    rue = addr[len(num)+1:].strip()
                else:
                    rue = addr
                way.tags['addr%d:street' % i] = rue
        way.tags['area'] = "yes"
        way.tags['ref:FR:CADASTRE:PARCELLE'] = parcelle.fid
        way.tags['source'] = SOURCE_TAG
    return osm

def generate_osm_adresses(parcelles, numeros_restant, transform):
    osm = Osm({'upload':'false'})
    # Numéros dont on a pas trouvé la (et donc la rue) parcelle associée
    for n in numeros_restant:
        if n:
            num, position, angle = n
            node = osm_add_point(osm, position, transform)
            node.tags['fixme'] = u"à vérifier et associer à la bonne rue"
            node.tags['addr:housenumber'] = num
            node.tags['source'] = SOURCE_TAG
    associatedStreets = {}
    # Adresse des parcelles:
    for parcelle in parcelles.itervalues():
        for num in parcelle.positions_numeros.keys():
            for i in range(len(parcelle.addrs_numeros[num])):
                #nom_parcelle = parcelle.fid[5:10].lstrip('0') + " " + parcelle.fid[10:].lstrip('0')
                num_parcelle = parcelle.fid[10:].lstrip('0')
                fixme = []
                if len(parcelle.positions_numeros[num]) > i:
                    position = parcelle.positions_numeros[num][i] 
                    # le numéro est souvent dessiné en dehors des limites
                    # de la parcelle, si c'est le cas et qu'il est proche des limites,
                    # on le déplace sur la limite:
                    if hasattr(parcelle,'limite') and \
                            (not position.within(parcelle.limite)) and \
                            (position.distance(parcelle.limite) < 2):
                        boundary = parcelle.limite.boundary
                        position = boundary.interpolate(boundary.project(position))
                else:
                    # on ne connait pas la position du numéro
                    # de cette adresse de la parcelle.
                    # on la fixe sur le label de la parcelle:
                    position = Point(parcelle.libellex, parcelle.libelley)
                    # Pour les petites parcelles, le label est parfois en dehors 
                    # de la parcelle, si c'est le cas on le déplace
                    # au centre de la parcelle:
                    if not position.within(parcelle.box):
                      position = parcelle.box.centroid
                    fixme.append(u"position à preciser, parcelle associée: n°" + num_parcelle)
                node = osm_add_point(osm, position, transform)
                node.tags['addr:housenumber'] = num
                node.tags['source'] = SOURCE_TAG
                rues = [addr[len(num)+1:].strip() for addr in parcelle.addrs_numeros[num]]
                for rue in rues:
                    if not associatedStreets.has_key(rue):
                        rel = Relation({})
                        rel.tags['type'] = 'associatedStreet'
                        rel.tags['name'] = rue
                        osm.add_relation(rel)
                        associatedStreets[rue] = rel
                    associatedStreets[rue].add_member(node, 'house')
                if len(rues) > 1:
                    fixme.append(u"choisir la bonne rue: " +
                        " ou ".join(rues))
                if hasattr(parcelle,'limite'):
                    limite = parcelle.limite
                else:
                    limite = parcelle.box
                distance = position.distance(limite)
                if distance > 10:
                    fixme.append(str(int(distance)) + u" m de la parcelle n°" + num_parcelle + u": vérifier la position et/ou la rue associée")
                    fixme.reverse()
                if fixme:
                    node.tags['fixme'] = " et ".join(fixme)
                  

    # Cherche les nom de lieus: toutes les adresse sans numéro qui ne sont pas des nom de rue:
    positions_des_lieus = {}
    for parcelle in parcelles.itervalues():
        for addr in parcelle.adresses:
            numero_match = NUMERO_RE.match(addr)
            if addr and (not numero_match) and (not associatedStreets.has_key(addr)):
                if not positions_des_lieus.has_key(addr):
                    positions_des_lieus[addr] = []
                if hasattr(parcelle,'limite') and parcelle.limite != None:
                    positions_des_lieus[addr].append(parcelle.limite.centroid)
                else:
                    positions_des_lieus[addr].append(parcelle.box.centroid)
    for lieu, positions in positions_des_lieus.iteritems():
        centre = MultiPoint(positions).centroid
        node = osm_add_point(osm, centre, transform)
        node.tags['place'] = 'neighbourhood'
        node.tags['name'] = lieu
        node.tags['source'] = SOURCE_TAG
        node.tags['fixme'] = u"à vérifier: lieu créé automatiquement à partir des adresses du coin"
    return osm



def parse_pdfs_parcelles_numeros_quartiers_nom_rues(pdfs):
    nb = [0, 0, 0, 0]
    parcelle_recognizer = ParcellePathRecognizer()
    nom_recognizer = NamePathRecognizer()
    numero_recognizer = HousenumberPathRecognizer()
    cadastre_parser = CadastreParser([parcelle_recognizer.handle_path, nom_recognizer.handle_path, numero_recognizer.handle_path])
    sys.stdout.write((u"Parse les exports PDF du cadastre:\n").encode("utf-8"))
    sys.stdout.flush()
    for filename in pdfs:
        cadastre_parser.parse(filename)
        new_nb = [len(parcelle_recognizer.parcelles), len(numero_recognizer.housenumbers), len(nom_recognizer.quartiers), len(nom_recognizer.rues)]
        diff = map(operator.sub, new_nb, nb)
        sys.stdout.write((filename + ": " + ", ".join([str(val) + " " + name for name,val in zip(["parcelles", u"numéros","quartiers", "noms"], diff)]) + "\n").encode("utf-8"))
        sys.stdout.flush()
        nb = new_nb
    return cadastre_parser.cadastre_projection, parcelle_recognizer.parcelles, numero_recognizer.housenumbers, nom_recognizer.quartiers, nom_recognizer.rues

def write_partitions_into_zip(node_list, filenameprefix, zip_output):
    if len(node_list) > TAILLE_PARTITIONEMENT_NOEUDS:
        partitions = partitionnement_osm_nodes(node_list , TAILLE_PARTITIONEMENT_NOEUDS)
        partitions = zip(*partitions)[0]
        taille_index = int(math.ceil(math.log10(len(partitions)+1)))
        for i in xrange(len(partitions)):
            osm = Osm({})
            for n in partitions[i]:
                osm.add_node(n)
            s = StringIO()
            OsmWriter(osm).write_to_stream(s)
            zip_output.writestr(filenameprefix + ("%%0%dd.osm" % taille_index) % (i+1,), s.getvalue())
    elif len(node_list) > 0:
        osm = Osm({})
        for n in node_list:
            osm.add_node(n)
        s = StringIO()
        OsmWriter(osm).write_to_stream(s)
        zip_output.writestr(filenameprefix + ".osm", s.getvalue())

def partitionnement_osm(osm, code_commune, zipfilename):
    """ partitionnement du fichier osm:
      - par rue pour les numéros associés à une seule rue
      - par k-moyenne pour les numéros orphelins, ambigus ou les quartiers.
    """
    zip_output = zipfile.ZipFile(zipfilename,"w", zipfile.ZIP_DEFLATED)

    relations_of_node = {}
    for n in osm.nodes.itervalues():
        relations_of_node[n.id()] = []
    for r in osm.relations.itervalues():
        for member in r.members:
            if member['type'] == 'node':
                relations_of_node[int(member['ref'])].append(r)
    # Cree un fichier par relation associatedStreet:
    for r in osm.relations.itervalues():
        assert(r.tags['type'] == 'associatedStreet')
        street_osm = Osm({})
        street_relation = Relation(r.attrs.copy(), r.tags.copy())
        street_osm.add_relation(street_relation)
        # FIXME: le découpage fait ici ne marche qu'avec les restriction suposée sur le fichier d'entrée (que des node et des relations, pas de way dans le fichier)
        for member in r.members:
            if member['type'] == 'node':
                i = int(member['ref'])
                if len(relations_of_node[i]) == 1:
                    node = osm.nodes[i]
                    street_osm.add_node(node)
                    street_relation.add_member(node, member['role'])
            else:
                street_relation.add_member(member)
        s = StringIO()
        OsmWriter(street_osm).write_to_stream(s)
        zip_output.writestr(
            code_commune + "/" + to_ascii(r.tags['name']) + ".osm",
            s.getvalue())
    # Partitionne les noeuds ambigus
    noeuds_ambigus = [osm.nodes[i] for i in relations_of_node.iterkeys() if
        len(relations_of_node[i]) > 1]
    write_partitions_into_zip(noeuds_ambigus, code_commune  + "/" "_AMBIGUS_", zip_output)
    # Partitionne les noeuds orphelins
    noeuds_orphelins = [osm.nodes[i] for i in relations_of_node.iterkeys() if
        ((len(relations_of_node[i]) == 0) and osm.nodes[i].tags.has_key('addr:housenumber'))]
    write_partitions_into_zip(noeuds_orphelins, code_commune + "/" "_ORPHELINS_", zip_output)
    # Partitionne les noeuds de quartiers (place=neighbourhood):
    noeuds_quartiers = [osm.nodes[i] for i in relations_of_node.iterkeys() if
        ((len(relations_of_node[i]) == 0) and osm.nodes[i].tags.has_key('place'))]
    write_partitions_into_zip(noeuds_quartiers, code_commune + "/" + "_QUARTIERS_", zip_output)
    zip_output.close()

    
            

def osm_add_point(osm, point, transform):
    if type(point) == Point:
      point = point.coords[0]
    lon,lat = transform(point)
    n = Node({'lon':str(lon),'lat':str(lat)})
    osm.add_node(n)
    return n

def osm_add_nodes_way(osm, nodes):
    way = Way({})
    osm.add_way(way)
    for node in nodes:
        way.add_node(node)
    return way
    
def osm_add_line_way(osm, line, transform):
    way = Way({})
    osm.add_way(way)
    for point in line.coords:
        way.add_node(osm_add_point(osm, point, transform))
    return way

def osm_add_polygon(osm, polygon, transform):
    for ring in polygon.interiors:
        osm_add_line_way(osm, ring, transform)
    way = osm_add_line_way(osm, polygon.exterior, transform)
    return way
     
#def parse_coordonnees_of_parcelles_xml(xml):
#    """parse le résultat xml d'une liste de parcelles du cadastre
#    retourne une table de hachage entre l'id de la parcelle et ses coordonées"""
#    tree = ET.fromstring(xml)
#    result = {}
#    for parcelle in tree:
#        id = parcelle.attrib['fid'][9:]
#        x = float(parcelle.iter("LIBELLEX").next().text)
#        y = float(parcelle.iter("LIBELLEY").next().text)
#        result[id] = (x,y)
#    return result

def named_chunks(l, n):
    """ Yield successive n-sized chunks from l.  """
    nb_chunks = (len(l) + n - 1) / n
    name_size = int(math.ceil(math.log10(nb_chunks+1)))
    name_format = "%%0%dd" % name_size
    for i,j in enumerate(xrange(0, len(l), n)):
        yield name_format % (i+1), l[j:j+n]

#def chunks(l, n):
#    """ Yield successive n-sized chunks from l.  """
#    for i in xrange(0, len(l), n):
#        yield l[i:i+n]
  

def decoupe_bbox_selon_taille_index(bbox, index, maxcount, basename):
    """ Découpe la bbox en une liste de bbox, chacune ne contenant pas plus de maxcount
        élément selont l'index spatial donné
    """
    if index.count(bbox) < maxcount:
        return [(basename, bbox)]
    else:
        xmin, ymin, xmax, ymax = bbox
        if abs(xmax-xmin) > abs(ymax-ymin):
            #print "decoupe x"
            xmiddle = (xmax+xmin) / 2
            bboxes = [ (xmin, ymin, xmiddle, ymax), (xmiddle, ymin, xmax, ymax) ]
            split_names = ["G", "D"] # gauche droite
        else:
            #print "decoupe y"
            ymiddle = (ymax+ymin) / 2
            bboxes = [ (xmin, ymin, xmax, ymiddle), (xmin, ymiddle, xmax, ymax) ]
            split_names = ["H","B"] # haut bas
        l1 = decoupe_bbox_selon_taille_index(bboxes[0], index, maxcount, basename + "-" + split_names[0])
        l2 = decoupe_bbox_selon_taille_index(bboxes[1], index, maxcount, basename + "-" + split_names[1])
        l1.extend(l2)
        return l1

def iter_download_parcelles_xml(cadastreWebsite, index_parcelles):
    # La requette vers le site du cadastre pour récupéré les fichiers xml correspondant au cadastre
    # est limité à 2000 résultats.
    # On utilise donc les limites extraites depuis les export pdf du cadastre pour creer un index spatial,
    # et évaluer le nombre de parcelles qui sont dans une zonne donnée, afin de la découper de tel sorte qu'il
    # ait moins de 2000 résultats.
    for name, bbox in decoupe_bbox_selon_taille_index(
            cadastreWebsite.get_bbox(), 
            index_parcelles, 
            MAX_PARCELLES_PAR_BBOX, 
            cadastreWebsite.code_commune + "-parcelles"):
        filename = name + ".xml"
        ok_filename = filename + ".ok"
        sys.stdout.write((filename + "\n").encode("utf-8"))
        sys.stdout.flush()
        if not (os.path.exists(filename) and os.path.exists(ok_filename)):
            if os.path.exists(filename): os.remove(filename)
            if os.path.exists(ok_filename): os.remove(ok_filename)
            xmlstring = cadastreWebsite.get_parcelles(*bbox)
            write_string_to_file(xmlstring, filename)
            open(ok_filename, 'a').close()
            time.sleep(ATTENTE_EN_SECONDE_ENTRE_DOWNLOAD)
        else:
            xmlstring = open(filename).read()
        yield xmlstring

def iter_download_parcelles_info_pdf(cadastreWebsite, ids_parcelles):
    ids_parcelles.sort()
    for name, ids in named_chunks(ids_parcelles, MAX_PARCELLES_PAR_INFO_PDF):
        filename = cadastreWebsite.code_commune + "-parcelles-" + name + ".pdf"
        ok_filename = filename + ".ok"
        sys.stdout.write((filename + "\n").encode("utf-8"))
        sys.stdout.flush()
        if not (os.path.exists(filename) and os.path.exists(ok_filename)):
            if os.path.exists(ok_filename): os.remove(ok_filename)
            write_stream_to_file(
                cadastreWebsite.open_pdf_infos_parcelles(ids),
                filename)
            open(ok_filename, 'a').close()
            time.sleep(ATTENTE_EN_SECONDE_ENTRE_DOWNLOAD)
        yield filename




#def integre_code_fantoir(osm, code_insee):
#    sys.stdout.write((u"Récupération des codes fantoir pour le code insee " 
#        + code_insee 
#        + "\ndepuis le site http://www.openstreetmap.fr/outils/adresses\n"
#        ).encode("utf-8"))
#    sys.stdout.flush()
##    mapping = get_mapping_nom_fantoir_vers_osm(code_insee)
#    for r in osm.relations.itervalues():
#        if r.tags.has_key('type') \
#                and r.tags['type'] == 'associatedStreet' \
#                and r.tags.has_key('name'):
#          nom_fantoir = r.tags['name']
#          if mapping.has_key(nom_fantoir):
#              ref_fantoir, nom_osm = mapping[nom_fantoir]
##              r.tags['ref:FR:FANTOIR'] = ref_fantoir
#              if nom_osm: 
#                 r.tags['name'] = nom_osm
  

def cadastre_vers_adresses(argv):
  download = True
  merge_adresses = True
  if len(argv) <= 1:
      command_line_open_cadastre(argv)
      return
  elif argv[1] in ["-h", "-help","--help"]:
      print_help()
      return
  elif argv[1] == "-data" :
      merge_adresses = False
      del(argv[1])
  elif argv[1] == "-nd" :
      download = False
      del(argv[1])
  if argv[1].startswith("-"):
      command_line_error(u"paramètres invalides")
  elif len(argv) == 2:
      error = command_line_open_cadastre(argv)
      if error: command_line_error(error)
  elif len(argv) > 3:
      command_line_error(u"trop d'arguments")
  else:
      try:
          cadastreWebsite = command_line_open_cadastre(argv)
          if type(cadastreWebsite) in [str, unicode]:
              command_line_error(cadastreWebsite, help=False)
              return
          else:
              code_departement = cadastreWebsite.code_departement
              code_commune = cadastreWebsite.code_commune
              nom_commune = cadastreWebsite.communes[code_commune]
              write_string_to_file("", code_commune + "-" + nom_commune + ".txt")
      except urllib2.URLError:
          if download:
              command_line_error(u"problème de connexion au site du cadastre")
              return
          else:
              sys.stdout.write(u"problème de connexion au site du cadastre\n".encode("utf-8"));
              code_departement = argv[1]
              code_commune = argv[2]
              nom_commune = "inconnu"
      if download:
          sys.stdout.write((u"Teléchargement des adresses cadastrales de la commune " + code_commune + " : " + nom_commune + "\n").encode("utf-8"))
          #sys.stdout.write((u"Téléchargement des exports PDF du cadastre.\n").encode("utf-8"))
          sys.stdout.flush()
          pdfs = iter_download_pdfs(cadastreWebsite, code_departement, code_commune)
          #sys.stdout.write((u"Conversion au format SVG:\n").encode("utf-8"))
          #svgs = pdfs_vers_svgs(pdfs)
      else:
          pdfs = glob.glob(code_commune + "-[0-9]-[0-9].pdf")
          pdfs.sort()

      projection, limite_parcelles, numeros, quartiers, nom_rues = parse_pdfs_parcelles_numeros_quartiers_nom_rues(pdfs)
      polygones_parcelles, index_polygones_parcelles = polygones_et_index_des_limite_parcelles(limite_parcelles)

      sys.stdout.write((u"Chargement des infos xml (id et position) d'environ %d parcelles:\n" % len(polygones_parcelles)).encode("utf-8"))
      sys.stdout.flush()
      if download:
          xmls = iter_download_parcelles_xml(cadastreWebsite, index_polygones_parcelles)
      else:
          xmls = imap(lambda f:open(f).read().decode("utf-8"), glob.glob(code_commune + "-parcelles*.xml"))
      parcelles = Parcelle.parse_xml_strings(xmls)

      info_pdf_count = (len(parcelles) + MAX_PARCELLES_PAR_INFO_PDF - 1) / MAX_PARCELLES_PAR_INFO_PDF
      sys.stdout.write((u"Chargement des infos pdf (adresses) des %d parcelles trouvées [%d pdfs]:\n" % (len(parcelles), info_pdf_count)).encode("utf-8"))
      sys.stdout.flush()
      if download:
          info_pdfs = iter_download_parcelles_info_pdf(cadastreWebsite, parcelles.keys())
      else:
          info_pdfs = glob.glob(code_commune + "-parcelles-*.pdf")
      for fid,adresses in parse_adresses_of_parcelles_info_pdfs(info_pdfs, code_commune).iteritems():
          parcelles[fid].adresses = adresses

      sys.stdout.write((u"Associe les limites et les parcelles.\n").encode("utf-8"))
      sys.stdout.flush()
      match_parcelles_et_limites(parcelles, polygones_parcelles, index_polygones_parcelles)

      transform = CadastreToOSMTransform(projection).transform_point

      # Ecrit un fichier OSM de résultat
      sys.stdout.write((u"Sauve fichiers de numéros, de parcelles et de noms.\n").encode("utf-8"))
      sys.stdout.flush()
      OsmWriter(generate_osm_housenumbers(numeros, transform)).write_to_file(code_commune + "-housenumbers.osm")
      OsmWriter(generate_osm_parcelles(parcelles, transform)).write_to_file(code_commune + "-parcelles.osm")
      osm_noms = generate_osm_noms(quartiers, nom_rues, transform)
      OsmWriter(osm_noms).write_to_file(code_commune + "-noms.osm")

      if merge_adresses:
          sys.stdout.write((u"Associe la position des numéros aux parcelles:\n").encode("utf-8"))
          sys.stdout.flush()
          match_parcelles_et_numeros(parcelles, numeros)

          # Ecrit un fichier OSM de résultat
          osm = generate_osm_adresses(parcelles, numeros, transform)

          # TODO: remplacer dans les numéros les lettres B,T et Q par
          # bis, ter ou quater si:
          # - pour un numéros dans une (ou des) relation(s) rue, il n'y a pas le
          #   meme numéro dans la rue avec une autre lettre que B T ou Q
          # - pour un numéros sans relation rue, si il n'y a pas dans les 150m? 
          #   le même numéro avec une autre lettre que B T ou Q
          #   pour ça ont doit pouvoir réutiliser l'index spatial utilise 
          #   dans la fonction match_parcelles_et_numeros()

          try:
              #integre_code_fantoir(osm, code_insee(code_departement, code_commune))
              addrfantoir.cherche_fantoir_et_osm_highways(code_departement, code_commune, osm, osm_noms)
          except:
              traceback.print_exc()
          OsmWriter(osm).write_to_file(code_commune + "-adresses.osm")
          partitionnement_osm(osm, code_commune, code_commune + "-adresses.zip")


if __name__ == '__main__':
    cadastre_vers_adresses(sys.argv)

