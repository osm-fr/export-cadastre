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

import re
import math
import time
import operator
import subprocess
import rtree.index
import xml.etree.ElementTree as ET
import shapely.geometry
from shapely.geometry         import Point
from shapely.geometry.polygon import Polygon



from cadastre_fr.osm         import Osm, Node, Way, OsmWriter
from cadastre_fr.osm_tools   import osm_add_polygon
from cadastre_fr.transform   import CadastreToOSMTransform
from cadastre_fr.recognizer  import ParcelPathRecognizer
from cadastre_fr.parser      import CadastreParser
from cadastre_fr.tools       import print_flush
from cadastre_fr.tools       import download_cached
from cadastre_fr.tools       import named_chunks
from cadastre_fr.housenumber import RE_NUMERO_CADASTRE
from cadastre_fr.globals import SOURCE_TAG


WAIT_BETWEEN_DOWNLOADS = 2
# Nombre max de parcelles pour par requête bbox:
MAX_PARCELS_PER_INFO_XML = 1500
# Nombre max de parcelles pour lesquelles on demande les info en une fois:
MAX_PARCELS_PER_INFO_PDF = 100

# Comparaison des valeurs calculées par rapport aux limites extraites des PDFs,
# avec les informations trouvées dans les fichiers XML des parcelles:
PARCEL_LIMIT_MATCH_BOUNDS_TOLERANCE = 1  # expressed in cadastre reference ~= meter
PARCEL_LIMIT_MATCH_AREA_TOLERANCE   = 10 # expressed in cadastre reference ~= square meter

# Les limites de parcelle vont se retrouver dupliquées sur plusieurs PDFs si
# elles sont à cheval.
# Nombre de décimal à comparer (après la virgule en mètre) pour éliminer les doublons:
PARCEL_LIMIT_ALMOST_EQUALS_DECIMAL = 1








def polygons_and_index_from_parcels_limits(parcels_limits):
    """Transforme les limites (liste de liste de coordonées) en polygone 
       Shapely et génère un index spatialisé avec leur bounds
       Retourne les polygons et l'index.
    """
    polygons = []
    index = rtree.index.Index()
    print_flush(u"Élimine les doublons dans les limites de parcelles")
    def already_present(p):
        # FIXME: cette recherche vas être quadratique si les intersections 
        # sont importantes, comme à Apatou en Guyane:
        center = p.centroid.coords[0]
        for i in index.intersection(center):
            if p.almost_equals(polygons[i], PARCEL_LIMIT_ALMOST_EQUALS_DECIMAL):
                return True
        return False
    def add_polygon(p):
        if not already_present(p):
            i = len(polygons)
            polygons.append(p)
            index.insert(i, p.bounds)
    for linear_rings in parcels_limits:
        add_polygon(Polygon(linear_rings[0], linear_rings[1:]))
        # Si nous avons un polygone creux, nous ajoutons aussi ses polygons
        # interieurs à la liste des limites:
        for linear_ring in linear_rings[1:]:
            add_polygon(Polygon(linear_ring))
    return polygons, index



def pdf_2_parcels_limits(pdf_filename_list):
    parcel_path_recognizer = ParcelPathRecognizer()
    cadastre_parser = CadastreParser([parcel_path_recognizer.handle_path])
    for pdf_filename in pdf_filename_list:
        cadastre_parser.parse(pdf_filename)
    parcels = parcel_path_recognizer.parcels
    print_flush(str(len(parcels)) +  " limites de parcelles")
    return cadastre_parser.cadastre_projection, parcels


def pdf_2_osm_parcels_limits(pdf_filename_list, osm_output):
    projection, parcels = pdf_2_parcels_limits(pdf_filename_list)
    cadastre_to_osm_transform = CadastreToOSMTransform(projection)
    osm = Osm({'upload':'false'})
    for parcel in parcels:
        for linear_ring in parcel:
            points = map(cadastre_to_osm_transform.transform_point, linear_ring)
            nodes = [Node({'lon':str(p.x), 'lat':str(p.y)}) for p in points]
            way = Way({})
            for n in nodes: 
                osm.add_node(n)
                way.add_node(n)
            osm.add_way(way)
    OsmWriter(osm).write_to_stream(osm_output)


def iter_download_parcels_info_xml(cadastreWebsite, parcels_index):
    # La requête vers le site du cadastre pour récupérer les fichiers xml correspondants
    # a une bbox est limité à 2000 résultats (2000 parcelles).
    # On utilise donc l'index spatial des limites extraites depuis les export pdf du cadastre
    # et évaluer le nombre de parcelles qui sont dans une zonne donnée, afin de la découper de tel sorte qu'il
    # y ait moins de 2000 résultats par requête.
    for name, bbox in bbox_split_against_index_size(
            cadastreWebsite.get_bbox(), 
            parcels_index, 
            MAX_PARCELS_PER_INFO_XML, 
            cadastreWebsite.code_commune + "-parcelles"):
        filename = name + ".xml"
        print_flush(filename)
        open_function = lambda: cadastreWebsite.open_parcels_xml(*bbox)
        if download_cached(open_function, filename):
            time.sleep(WAIT_BETWEEN_DOWNLOADS)
        with open(filename) as f:
            xmlstring = f.read().decode("utf-8")
        yield filename


def bbox_split_against_index_size(bbox, index, maxcount, basename):
    """ Découpe la bbox en une liste de bbox, chacune ne contenant pas plus de maxcount
        éléments selon l'index spatial donné
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
        l1 = bbox_split_against_index_size(bboxes[0], index, maxcount, basename + "-" + split_names[0])
        l2 = bbox_split_against_index_size(bboxes[1], index, maxcount, basename + "-" + split_names[1])
        l1.extend(l2)
        return l1


def iter_download_parcels_info_pdf(cadastreWebsite, parcels_ids):
    parcels_ids.sort()
    for name, ids in named_chunks(parcels_ids, MAX_PARCELS_PER_INFO_PDF):
        filename = cadastreWebsite.code_commune + "-parcelles-" + name + ".pdf"
        print_flush(filename)
        open_function = lambda: cadastreWebsite.open_parcels_infos_pdf(ids)
        if download_cached(open_function, filename):
            time.sleep(WAIT_BETWEEN_DOWNLOADS)
        yield filename



class ParcelInfo(object):
    def __init__(self, fid, nature="", libellex=0.0, libelley=0.0,
            xmin=0.0,ymin=0,xmax=0.0,ymax=0.0,surfacegeom=0.0,
            limite=None):
        self.__dict__.update(locals()); del self.self
        self.bounds = (self.xmin, self.ymin, self.xmax, self.ymax)
        self.area = surfacegeom
        self.box = shapely.geometry.box(*self.bounds)

    @staticmethod
    def parse_xmls(xmls):
        """parse le résultat xml d'une liste de parcelles du cadastre"""
        # utilise une table de hachage pour suprimier le éléments redondants:
        resultmap = {}
        for xml in xmls:
            tree = ET.parse(xml).getroot()
            for parcel in tree:
                param = {attr.replace("_","") : float(get_xml_child_text(parcel, attr.upper(), "0"))
                    for attr in
                    ["libellex", "libelley", "x_min","x_max","y_min","y_max","surface_geom"]}
                    # La commune de Vizille (38) n'as parfois pas de champ
                    # libellex et libelley.
                fid  = parcel.attrib['fid'][9:]
                resultmap[fid] = ParcelInfo(
                    fid  = fid, 
                    nature = parcel.iter("NATURE").next().text,
                    **param)
        return resultmap


def parse_addresses_of_parcels_info_pdfs(pdfs, code_commune):
    """parse le pdf d'info des parcelles du cadastre,
       retourne une table de hachage entre l'id des parcelles
       et une liste d'adresses"""
    parcels_addresses = {}
    code_postal_re =  re.compile("(.*)^[0-9]{5}.*", re.S|re.M)
    for filename in pdfs:
        txt = subprocess.check_output(["pdftotext", filename, "-"]).decode("utf-8")
        mode_address = False
        for line in txt.splitlines():
            line = line.strip()
            if line.startswith(u"Service de la Documentation Nationale du Cadastre") \
                    or line.startswith(u"82, rue du Maréchal Lyautey - 78103 Saint-Germain-en-Laye Cedex") \
                    or line.startswith(u"SIRET 16000001400011") \
                    or line.startswith(u"Informations sur la feuille éditée par internet le ") \
                    or line.startswith(u"©201"): # ©2012 Ministère de l'Économie et des Finances
                continue
            #print line
            if line.startswith(u"Références de la parcelle "):
                ids = line[len(u"Références de la parcelle "):].strip()
                if len(ids.split(" ")) == 2:
                    # Cas rencontré sur la commune de Mauves, Ardèche
                    # Seulement 2 ids, on assume la valeur 0 pour le 3ème:
                    id1,id2 = ids.split(" ")
                    id3 = "0"
                else:
                    id1,id2,id3 = ids.split(" ")
                if len(id2) ==1:
                   id2 = "0" + id2
                id3 = "%04d" % int(id3)
                id_parcel = str(code_commune + id1 + id2 + id3)
                addresses = []
                parcels_addresses[id_parcel] = addresses
                mode_address = False
            elif line == u"Adresse":
                addresses.append("")
                mode_address = True
            elif mode_address and len(line) > 0:
                if len(addresses[-1]) == 0:
                    addresses[-1] = line
                else:
                    addresses[-1] = addresses[-1] + '\n' + line

    # Supprimme la fin de l'adresse à partir du code postal
    # et remplace les retours à la ligne par un espace:
    # Enlève aussi les doublons avec un set(), car si une parcelle 
    # a deux fois exactement la même adresse, cela vas faire planter l'algo 
    # de la fonction match_parcels_and_numbers
    # comme par exemple à Beauvais (département 60 code commune O0057)
    # Remplace aussi les adresses du type
    #    1 à 3 RUE DE LA NEUVILLE
    #    02510 IRON
    # par deux adresses:
    #    1 RUE DE LA NEUVILLE
    #    3 RUE DE LA NEUVILLE
    NUM_1_A_NUM_2_RE = re.compile("^(" + RE_NUMERO_CADASTRE.pattern + u") \xe0 (" + RE_NUMERO_CADASTRE.pattern[1:] + ")\s(.*)$")
    for id_parcel, addresses in parcels_addresses.iteritems():
        addresses_set = set()
        for address in addresses:
            match_code_postal = code_postal_re.match(address)
            if match_code_postal:
                address = match_code_postal.group(1)
            address = address.replace("\n"," ").strip()
            num_1_a_num_2_match = NUM_1_A_NUM_2_RE.match(address)
            if num_1_a_num_2_match:
                print_flush(u"ATTENTION: adresse comportant un intervalle: " + address)
                # On a une adresse du type "1 à 3 RUE DE LA NEUVILLE"
                NUM_1_GROUP_INDEX = 1
                NUM_2_GROUP_INDEX = NUM_1_GROUP_INDEX + RE_NUMERO_CADASTRE.pattern.count("(") + 1
                RUE_GROUP_INDEX = NUM_2_GROUP_INDEX + RE_NUMERO_CADASTRE.pattern.count("(") + 1
                num1 = int(num_1_a_num_2_match.group(NUM_1_GROUP_INDEX))
                num2 = int(num_1_a_num_2_match.group(NUM_2_GROUP_INDEX))
                rue = num_1_a_num_2_match.group(RUE_GROUP_INDEX)
                for i in range(num1, num2 + 2, 2):
                    addr_i = u"%d %s" % (i, rue)
                    print_flush(u"    ajoute l'adresse: " + adr_i)
                    addresses_set.add(addr_i)
            else:
                addresses_set.add(address)
        parcels_addresses[id_parcel] = list(addresses_set)

    return parcels_addresses
 


def match_parcels_and_limits(parcels, limits, limits_index):
    """Affecte le champs .limit de chaque parcelles avec celle
    parmis la liste des limites données qui correspond, en 
    comparant la bounding box (.bounds) et à l'area (.area) 
    """
    #max_diff_bounds = 0
    #max_diff_area = 0
    for parcel in parcels.itervalues():
        best_diff = float("inf")
        best_limit = None
        center = parcel.box.centroid.coords[0]
        for i in limits_index.intersection(center):
            limit = limits[i]
            if abs(parcel.area - limit.area) < PARCEL_LIMIT_MATCH_AREA_TOLERANCE:
                diff = bounds_diff(parcel.bounds, limit.bounds)
                if diff < best_diff:
                    best_diff = diff
                    best_limit = limit
        if best_limit and \
                best_diff < PARCEL_LIMIT_MATCH_BOUNDS_TOLERANCE:
                #and abs(parcel.area-best_limit.area) < PARCEL_LIMIT_MATCH_AREA_TOLERANCE:
            parcel.limit = best_limit
            #max_diff_bounds = max(max_diff_bounds, best_diff)
            #max_diff_area = max(max_diff_area, abs(parcel.area - best_limit.area))
        else:
            print_flush(u"ATTENTION: limites non trouvée pour la parcelle " + parcel.fid)
    #print "---"          
    #print "max diff parcels bounds: " + str(max_diff_bounds)
    #print "max diff parcels area: " + str(max_diff_area)
    #transform = CadastreToOSMTransform(projection).transform_point
    #osm = Osm({})
    #for i in range(len(limits)):
    #    limit = limits[i]
    #    if limit:
    #        way = osm_add_polygon(osm, limit, transform)
    #        way.tags["bounds"] = str(limit.bounds)
    #        way.tags["area"] = str(limit.area)
    #        way.tags["index"] = str(i)
    #for parcel in parcels.itervalues():
    #    if not parcel.ok:
    #        way = osm_add_polygon(osm, parcel.limit, transform)
    #        way.tags["bounds"] = str(parcel.bounds)
    #        way.tags["area"] = str(parcel.area)
    #        way.tags["name"] = parcel.fid
    #OsmWriter(osm).write_to_file("l.osm")




def match_parcels_and_housenumbers(parcels, numbers):
    numbers_index = rtree.index.Index()
    print_flush(str(len(numbers)) + u" numéros à trouver")
    # Convertit les positions des numéros en Point et insere les dans l'index:
    for i,(num, position, angle) in enumerate(numbers):
        position = Point(tuple(position))
        numbers[i] = num, position, angle
        numbers_index.insert(i, position.coords[0])
    # Cherche la liste des numeros contenus dans les adresses de la parcelle:
    parcels_of_addresses = {}
    for parcel in parcels.itervalues():

        # Liste d'adresses de la parcelle, indexé par leur numéro:
        parcel.addrs_numbers = {}

        # Liste de position des numéros des adresse. Pour un numéro donné
        # on cherchera autant de position que la parcelle a d'adresse avec ce numéro
        parcel.positions_numbers = {}
        parcel.num_to_find = 0
        if not hasattr(parcel, 'addresses'):
            parcel.addresses = []
        else:
            for addr in parcel.addresses:
                if not parcels_of_addresses.has_key(addr):
                    parcels_of_addresses[addr] = []
                parcels_of_addresses[addr].append(parcel)
                number_match = RE_NUMERO_CADASTRE.match(addr)
                if number_match:
                    number = number_match.group(0)
                    if not parcel.positions_numbers.has_key(number):
                        parcel.positions_numbers[number] = []
                        parcel.addrs_numbers[number] = []
                    parcel.addrs_numbers[number].append(addr)
                    parcel.num_to_find += 1
    for distance in [0,1,2,3] + range(4,50,2) + range(50,200,5):
        nb_found_with_limit = 0
        nb_found_with_bbox = 0
        # cherche la position des numeros contenus ou à proximité des parcelles
        for parcel in parcels.itervalues():
            if parcel.num_to_find > 0:
                if hasattr(parcel, 'limit') and parcel.limit != None:
                    if distance == 0:
                        #print "choix parcel.limit"
                        limit_etendue = parcel.limit
                    else:
                        #print "choix parcel.limit.buffer"
                        limit_etendue = parcel.limit.buffer(distance)
                elif distance == 50:
                    # On ne connait pas les limites de la parcel, ont utilise
                    # sa bounding box - 50m par sécurité:
                    #print "choix parcel.box"
                    limit_etendue = parcel.box
                elif distance > 50:
                    #print "choix parcel.box.buffer"
                    limit_etendue = parcel.box.buffer(distance-50)
                else:
                    limit_etendue = None
                if limit_etendue != None:
                    #print "Limite de la parcelle " + parcel.fid + " etendue de " + str(distance)
                    #print limit_etendue
                    #print "exterior: " + str(limit_etendue.exterior.coords[:])
                    #for i in limit_etendue.interiors:
                    #    print "interiors: " + str(i.coords[:])
                    #print "bounds: " + str(limit_etendue.bounds)
                    for i in numbers_index.intersection(limit_etendue.bounds):
                        if numbers[i]:
                            num, position, angle = numbers[i]
                            if position.within(limit_etendue):
                              if num == "6" or num == "9":
                                  # Avec la nouvelle Police de caracètres utilisée par le cadastre
                                  # on n'est pas capable de faire la différence ente un 6 et un 9
                                  # donc si le numéro était un 6 on considère que c'était peut être aussi un 9...
                                  num_possibilities = ["6","9"]
                              else:
                                  num_possibilities = [num,]
                              for num in num_possibilities:
                                if parcel.positions_numbers.has_key(num) and \
                                        (len(parcel.positions_numbers[num]) < len(parcel.addrs_numbers[num])):
                                        # on a vérifie qu'il faut encore trouver ce numéro pour une des adresses
                                        # de cette parcel:
                                    parcel.positions_numbers[num].append((position, angle))
                                    parcel.num_to_find -= 1
                                    # marque le numéro comme trouvé et enlève le de l'index:
                                    numbers[i] = None
                                    numbers_index.delete(i, position.coords[0])
                                    if hasattr(parcel,'limit'):
                                        nb_found_with_limit += 1
                                    else:
                                        nb_found_with_bbox += 1
                                    # On parcourt la liste des parcelles qui cherchaient la même adresse
                                    # pour leur dire que c'est foutu pour elle, c'est nous qui s'approprions le numéro !
                                    addr = parcel.addrs_numbers[num][len(parcel.positions_numbers[num])-1]
                                    for p in parcels_of_addresses[addr]:
                                        if p != parcel:
                                            p.addresses.remove(addr)
                                            p.addrs_numbers[num].remove(addr)
                                            if len(p.addrs_numbers[num]) == 0:
                                                del(p.addrs_numbers[num])
                                                del(p.positions_numbers[num])
                                            p.num_to_find -= 1
                                    break # for num in num_possibilities:

        if nb_found_with_limit>0:
            print_flush(str(nb_found_with_limit) + u" numéros trouvés à moins de " + str(distance) + u"m des limites des parcelles")
        if nb_found_with_bbox>0:
            print_flush(str(nb_found_with_bbox) + u" numéros trouvés à moins de " + str(distance-50) + u"m des bbox des parcelles")
    nb_numbers_unatached = 0
    for n in numbers:
        if n:
            nb_numbers_unatached +=1
    if nb_numbers_unatached == 1:
        print_flush("ATTENTION: " + str(nb_numbers_unatached) + u" numéro non rataché à son adresse !")
    elif nb_numbers_unatached > 1:
        print_flush("ATTENTION: " + str(nb_numbers_unatached) + u" numéros non ratachés à leur adresse !")
    else:
        print_flush(u"Tous les numéros ont trouvé une parcelle !")
    count_not_found = 0
    for parcel in parcels.itervalues():
      count_not_found += parcel.num_to_find
    if count_not_found == 1:
        print_flush("ATTENTION: " + str(count_not_found) + u" adresse n'a pas trouvé son numéro !")
    elif count_not_found > 1:
        print_flush("ATTENTION: " + str(count_not_found) + u" adresses n'ont pas trouvé leur numéro !")
    else:
        print_flush(u"Toutes les adresses ont trouvé leur numéro!")


def generate_osm_parcels(parcels, transform):
    osm = Osm({'upload':'false'})
    for parcel in parcels.itervalues():
        if hasattr(parcel,"limit") and parcel.limit != None:
            limit = parcel.limit
        else:
            limit = parcel.box
        way = osm_add_polygon(osm, limit, transform)
        if hasattr(parcel, 'addresses'):
            for i,addr in enumerate(parcel.addresses):
                number_match = RE_NUMERO_CADASTRE.match(addr)
                if number_match:
                    num = number_match.group(0)
                    way.tags['addr%d:housenumber' % i] = num
                    rue = addr[len(num)+1:].strip()
                else:
                    rue = addr
                way.tags['addr%d:street' % i] = rue
        way.tags['area'] = "yes"
        way.tags['ref:FR:CADASTRE:PARCELLE'] = parcel.fid
        way.tags['source'] = SOURCE_TAG
    return osm


def get_xml_child_text(e, tag, default=None):
    """ return the text of the child element tag of xml element e
        or default if no child has tag exist.
    """
    try:
        return e.iter(tag).next().text
    except StopIteration:
        return default

def bounds_diff(bounds1, bounds2):
    return max([abs(operator.sub(*t)) for t in zip(bounds1, bounds2)])
