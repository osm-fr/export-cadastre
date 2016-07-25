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

#import pdb;pdb_set_trace()

import re
import sys
import math
import time
import glob
import zipfile
import os.path
import operator
import traceback
import itertools
from cStringIO import StringIO
try:
    import rtree.index
except:
    traceback.print_exc()
    sys.stderr.write("Please install Rtree (pip install rtree)\n")
    sys.exit(-1)
try:
    import shapely.ops
    import shapely.geometry
    import shapely.prepared
    from shapely.geometry import Point
    from shapely.geometry import MultiPoint
    from shapely.geometry import LineString
    from shapely.geometry.polygon import Polygon
    from shapely.geometry.multipolygon import MultiPolygon
except:
    traceback.print_exc()
    sys.stderr.write("Please install Shapely (pip install shapely)\n")
    sys.exit(-1)


from cadastre_fr.osm           import Osm, Node, Way, Relation, OsmParser, OsmWriter
from cadastre_fr.name          import zip_osm_names
from cadastre_fr.name          import generate_osm_names
from cadastre_fr.name          import generate_osm_small_names
from cadastre_fr.name          import generate_osm_street_names
from cadastre_fr.name          import generate_osm_lieuxdits_names
from cadastre_fr.tools         import to_ascii
from cadastre_fr.tools         import print_flush
from cadastre_fr.tools         import named_chunks
from cadastre_fr.tools         import download_cached
from cadastre_fr.tools         import command_line_error
from cadastre_fr.tools         import write_string_to_file
from cadastre_fr.tools         import write_stream_to_file
from cadastre_fr.parcel        import ParcelInfo
from cadastre_fr.parcel        import generate_osm_parcels
from cadastre_fr.parcel        import match_parcels_and_limits
from cadastre_fr.parcel        import MAX_PARCELS_PER_INFO_PDF
from cadastre_fr.parcel        import iter_download_parcels_info_xml
from cadastre_fr.parcel        import iter_download_parcels_info_pdf
from cadastre_fr.parcel        import match_parcels_and_housenumbers
from cadastre_fr.parcel        import parse_addresses_of_parcels_info_pdfs
from cadastre_fr.parcel        import polygons_and_index_from_parcels_limits
from cadastre_fr.parser        import CadastreParser
from cadastre_fr.fantoir       import cherche_fantoir_et_osm_highways
from cadastre_fr.fantoir       import get_osm_buildings_and_barrier_ways
from cadastre_fr.globals       import SOURCE_TAG
from cadastre_fr.website       import code_insee
from cadastre_fr.website       import CadastreWebsite
from cadastre_fr.website       import command_line_open_cadastre_website
from cadastre_fr.geometry      import incidence
from cadastre_fr.geometry      import BoundingBox
from cadastre_fr.geometry      import cartesien_2_polaire
from cadastre_fr.osm_tools     import osm_add_point
from cadastre_fr.osm_tools     import osm_add_polygon
from cadastre_fr.osm_tools     import osm_add_multipolygon
from cadastre_fr.osm_tools     import nearest_intersection 
from cadastre_fr.osm_tools     import osm_add_way_direction
from cadastre_fr.transform     import CadastreToOSMTransform
from cadastre_fr.transform     import OSMToCadastreTransform
from cadastre_fr.recognizer    import NamePathRecognizer
from cadastre_fr.recognizer    import ParcelPathRecognizer
from cadastre_fr.recognizer    import HousenumberPathRecognizer
from cadastre_fr.housenumber   import RE_NUMERO_CADASTRE
from cadastre_fr.housenumber   import generate_osm_housenumbers
from cadastre_fr.housenumber   import determine_osm_parcels_bis_ter_quater
from cadastre_fr.housenumber   import determine_osm_addresses_bis_ter_quater
from cadastre_fr.download_pdf  import download_pdfs
from cadastre_fr.partitioning  import partition_osm_nodes
from cadastre_fr.partitioning  import partition_osm_nodes_filename_map



FIXME_JOINDRE_NOEUD_AU_WAY = u"Joindre le nœud au bâtiment (J)"
MAX_BUILDING_DISTANCE_METERS = 2
NODE_INSIDE_BUILDING_DISTANCE_MARGIN = 0.1



def cadastre_2_osm_addresses(cadastreWebsite, code_departement, code_commune,  nom_commune, download, bis, merge_addresses, use_external_data, split_result):
    if download:
        print_flush(u"Teléchargement des adresses cadastrales de la commune " + code_commune + " : " + nom_commune)
        pdfs = download_pdfs(cadastreWebsite, code_departement, code_commune)
    else:
        pdfs = glob.glob(code_commune + "-[0-9]*-[0-9]*.pdf")
        pdfs.sort()
        if len(pdfs) == 0:
            command_line_error(u"Aucun PDF téléchargé")
            return
    projection, parcels_limits, housenumbers, lieuxdits_names, street_names, small_names = \
            parse_pdfs_for_parcels_housenumbers_lieuxdits_street_names(pdfs)
    parcels_polygons, parcels_index = polygons_and_index_from_parcels_limits(parcels_limits)

    print_flush(u"Chargement des infos xml (id et position) d'environ %d parcelles:" % len(parcels_polygons))
    if download:
        xmls = iter_download_parcels_info_xml(cadastreWebsite, parcels_index)
    else:
        xmls = glob.glob(code_commune + "-parcelles*.xml")
        if len(xmls) == 0:
            command_line_error(u"Aucune info XML des parcelles déjà téléchargés")
            return
    parcels = ParcelInfo.parse_xmls(xmls)

    info_pdf_count = (len(parcels) + MAX_PARCELS_PER_INFO_PDF - 1) / MAX_PARCELS_PER_INFO_PDF
    print_flush(u"Chargement des infos pdf (adresses) des %d parcelles trouvées [%d pdfs]:" % (len(parcels), info_pdf_count))
    if download:
        info_pdfs = iter_download_parcels_info_pdf(cadastreWebsite, parcels.keys())
    else:
        info_pdfs = glob.glob(code_commune + "-parcelles-*.pdf")
        if len(info_pdfs) == 0:
            command_line_error(u"Aucun info PDF des parcelles n'a été téléchargée")
            return
    for fid, addresses in parse_addresses_of_parcels_info_pdfs(info_pdfs, code_commune).iteritems():
        if fid in parcels:
            parcels[fid].addresses = addresses
        else:
            # Problème rencontré sur la ville de Vitry-sur-Seine (94):
            # Lorsque l'on demande les info pdf de parcelle Z0081000AL00DP 
            # le fichier pdf résultat remplace l'id par Z0081000AL0000 et il
            # ne contient aucune adresse correspondante.
            print_flush(u"ERREUR sur un id de parcelle invalide: " + fid)


    print_flush(u"Associe les limites et les parcelles.")
    match_parcels_and_limits(parcels, parcels_polygons, parcels_index)

    transform_to_osm = CadastreToOSMTransform(projection).transform_point
    transform_from_osm = OSMToCadastreTransform(projection).transform_point

    # Ecrit un fichier OSM de résultat
    print_flush(u"Sauve fichiers de numéros, de parcelles et de noms.")
    OsmWriter(generate_osm_housenumbers(housenumbers, transform_to_osm)).write_to_file(code_commune + "-housenumbers.osm")
    osm_parcels = generate_osm_parcels(parcels, transform_to_osm)


    if bis: determine_osm_parcels_bis_ter_quater(osm_parcels)
    OsmWriter(osm_parcels).write_to_file(code_commune + "-parcelles.osm")
    osm_mots = generate_osm_names(lieuxdits_names, street_names, small_names, transform_to_osm)
    OsmWriter(osm_mots).write_to_file(code_commune + "-mots.osm")
    zip_osm_names(
      generate_osm_lieuxdits_names(lieuxdits_names, transform_to_osm),
      generate_osm_street_names(street_names, transform_to_osm),
      generate_osm_small_names(small_names, transform_to_osm),
      code_commune + "-mots.zip", 
      code_commune + "-mots");

    if merge_addresses:
        print_flush(u"Associe la position des numéros aux parcelles:")
        match_parcels_and_housenumbers(parcels, housenumbers)

        # Ecrit un fichier OSM de résultat
        osm = generate_osm_addresses(parcels, housenumbers, transform_to_osm)

        # TODO: remplacer dans les numéros les lettres B,T et Q par
        # bis, ter ou quater si:
        # - pour un numéros dans une (ou des) relation(s) rue, il n'y a pas le
        #   meme numéro dans la rue avec une autre lettre que B T ou Q
        # - pour un numéros sans relation rue, si il n'y a pas dans les 150m? 
        #   le même numéro avec une autre lettre que B T ou Q
        #   pour ça ont doit pouvoir réutiliser l'index spatial utilise 
        #   dans la fonction match_parcels_and_housenumbers()
        if bis: determine_osm_addresses_bis_ter_quater(osm)

        if use_external_data:
            try:
                cherche_fantoir_et_osm_highways(code_departement, code_commune, osm, osm_mots)
            except:
                traceback.print_exc()

        transform_place_into_highway(osm)

        OsmWriter(osm).write_to_file(code_commune + "-adresses.osm")
        if split_result:
            partition_osm_associatedStreet_zip(osm, code_commune + "-adresses.zip", code_commune + "-adresses")

        if use_external_data:
            try:
                cherche_osm_buildings_proches(code_departement, code_commune, osm, transform_to_osm, transform_from_osm)
                OsmWriter(osm).write_to_file(code_commune + "-adresses_buildings_proches.osm")
                if split_result:
                    partition_osm_associatedStreet_zip(osm, code_commune + "-adresses_buildings_proches.zip", code_commune + "-adresses")
            except:
                traceback.print_exc()
    
    try:
        print_flush(u"Génère fichiers de lieux-dits")
        osm_lieuxdits = generate_osm_limit_lieuxdits(parcels, transform_to_osm)
        OsmWriter(osm_lieuxdits).write_to_file(code_commune + "-lieux-dits.osm")
        if split_result:
            partition_osm_lieuxdits_zip(osm, osm_lieuxdits, code_commune + "-lieux-dits.zip", code_commune + "-lieux-dits")
    except:
        traceback.print_exc()




def parse_pdfs_for_parcels_housenumbers_lieuxdits_street_names(pdfs):
    nb = [0, 0, 0, 0, 0]
    parcel_recognizer = ParcelPathRecognizer()
    name_recognizer = NamePathRecognizer()
    housenumber_recognizer = HousenumberPathRecognizer()
    cadastre_parser = CadastreParser([parcel_recognizer.handle_path, name_recognizer.handle_path, housenumber_recognizer.handle_path])
    print_flush(u"Parse les exports PDF du cadastre:")
    for filename in pdfs:
        cadastre_parser.parse(filename)
        new_nb = [len(parcel_recognizer.parcels), len(housenumber_recognizer.housenumbers), len(name_recognizer.lieuxdits), len(name_recognizer.street_names), len(name_recognizer.small_names)]
        diff = map(operator.sub, new_nb, nb)
        print_flush(filename + ": " + ", ".join([str(val) + " " + name for name,val in zip(["parcelles", u"numéros","lieux-dits", "noms", "petits noms"], diff)]))
        nb = new_nb
    return cadastre_parser.cadastre_projection, parcel_recognizer.parcels, housenumber_recognizer.housenumbers, name_recognizer.lieuxdits, name_recognizer.street_names, name_recognizer.small_names






def generate_osm_limit_lieuxdits(parcels, transform):
    osm = Osm({'upload':'false'})
    lieuxdits = {}
    for parcel in parcels.itervalues():
        if hasattr(parcel, 'addresses'):
            if hasattr(parcel,"limit") and parcel.limit != None:
                limit = parcel.limit
            else:
                limit = parcel.box
            for addr in parcel.addresses:
                if addr and not RE_NUMERO_CADASTRE.match(addr):
                    # Pas de numéro, on considère que l'adresse est un nom de lieux-dits
                    if addr in lieuxdits:
                        lieuxdits[addr] = lieuxdits[addr].union(limit)
                    else:
                        lieuxdits[addr] = limit
    for nom,limit in lieuxdits.iteritems():
        limit = limit.simplify(0.5, preserve_topology=True)
        o = osm_add_multipolygon(osm, limit, transform)
        o.tags['name'] = nom
        o.tags['place'] = "locality"
        o.tags['source'] = SOURCE_TAG
    return osm


def generate_osm_addresses(parcels, numbers_left, transform):
    osm = Osm({'upload':'false'})
    # Numéros dont on a pas trouvé la parcelle associée (et donc la rue)
    for n in numbers_left:
        if n:
            num, position, angle = n
            node = osm_add_point(osm, position, transform)
            node.tags['fixme'] = u"à vérifier et associer à la bonne rue"
            if num == "6" or num == "9":
                num = "6 ou 9"
                node.tags['fixme'] = u"ATTENTION: 6 peut être confondu avec 9, vérifier sur le cadastre."
            node.tags['addr:housenumber'] = num
            node.tags['source'] = SOURCE_TAG
            node.angle = angle
            node.limit_parcel = None
    associatedStreets = {}
    # Adresse des parcelles:
    for parcel in parcels.itervalues():
        for num in parcel.positions_numbers.keys():
            for i in range(len(parcel.addrs_numbers[num])):
                #nom_parcele = parcel.fid[5:10].lstrip('0') + " " + parcel.fid[10:].lstrip('0')
                num_parcel = parcel.fid[10:].lstrip('0')
                fixme = []
                if len(parcel.positions_numbers[num]) > i:
                    position, angle = parcel.positions_numbers[num][i] 
                    # le numéro est souvent dessiné en dehors des limites
                    # de la parcelle, si c'est le cas et qu'il est proche des limites,
                    # on le déplace sur la limite:
                    if hasattr(parcel,'limit') and \
                            (parcel.limit != None) and \
                            (not position.within(parcel.limit)) and \
                            (position.distance(parcel.limit) < 2):
                        boundary = parcel.limit.boundary
                        position = boundary.interpolate(boundary.project(position))
                else:
                    # on ne connait pas la position du numéro
                    # de cette adresse de la parcelle.
                    # on la fixe sur le label de la parcelle:
                    position = Point(parcel.libellex, parcel.libelley)
                    # Pour les petites parcelles, le label est parfois en dehors 
                    # de la parcelle, si c'est le cas on le déplace
                    # au centre de la parcelle:
                    if not position.within(parcel.box):
                      position = parcel.box.centroid
                    fixme.append(u"position à preciser, parcelle associée: n°" + num_parcel)
                    angle = None
                node = osm_add_point(osm, position, transform)
                node.angle = angle
                if hasattr(parcel,'limit'):
                    node.limit_parcel = parcel.limit
                else:
                    node.limit_parcel = None
                node.tags['addr:housenumber'] = num
                node.tags['source'] = SOURCE_TAG
                rues = [addr[len(num)+1:].strip() for addr in parcel.addrs_numbers[num]]
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
                if hasattr(parcel,'limit') and parcel.limit != None:
                    limit = parcel.limit
                else:
                    limit = parcel.box
                distance = position.distance(limit)
                if distance > 10:
                    fixme.append(str(int(distance)) + u" m de la parcelle n°" + num_parcel + u": vérifier la position et/ou la rue associée")
                    fixme.reverse()
                if fixme:
                    node.tags['fixme'] = " et ".join(fixme)


    # Cherche les nom de lieus: toutes les adresse sans numéro qui ne sont pas des nom de rue:
    positions_des_lieus = {}
    for parcel in parcels.itervalues():
        for addr in parcel.addresses:
            number_match = RE_NUMERO_CADASTRE.match(addr)
            if addr and (not number_match) and (not associatedStreets.has_key(addr)):
                if not positions_des_lieus.has_key(addr):
                    positions_des_lieus[addr] = []
                if hasattr(parcel,'limit') and parcel.limit != None:
                    centroid = parcel.limit.centroid
                    if centroid.wkt == 'GEOMETRYCOLLECTION EMPTY':
                        # Pour la ville de Kingersheim (68), il existe une limite de parcelle
                        # aplatie (sur une ligne, donc d'area nulle) ce qui lui donne
                        # un centroid vide.
                        # On utilise alors le centre des points composant sa limite exteieur
                        centroid = parcel.limit.exterior.centroid
                    positions_des_lieus[addr].append(centroid)
                else:
                    positions_des_lieus[addr].append(parcel.box.centroid)
    for lieu, positions in positions_des_lieus.iteritems():
        centre = MultiPoint(positions).centroid
        node = osm_add_point(osm, centre, transform)
        node.tags['name'] = lieu
        node.tags['source'] = SOURCE_TAG
        if lieu.lower().startswith("hameau "):
            node.tags['place'] = 'hamlet'
        else:
            node.tags['place'] = ''
    return osm


def transform_place_into_highway(osm):
    """Transforme les place=* dont le nom ressemble à un nom de rue"""
    for n in osm.nodes.itervalues():
        if n.id()<0 and "place" in n.tags:
            if "name" in n.tags and n.tags["name"].split()[0].lower() in ["rue","impasse","chemin","passage","route","avenue","boulevard"]:
                del(n.tags["place"])
                n.tags["highway"] = "road"
                n.tags["fixme"] = u"à vérifier: nom créé automatiquement à partir des adresses du coin"
    return



def partition_osm_associatedStreet_zip(osm, zip_filename, subdir=""):
    """ partitioning du fichier osm:
      - par rue pour les numéros associés à une seule rue
      - par k-moyenne pour les numéros orphelins, ambigus
    """
    filename_osm_map = {}
    if subdir: subdir += "/"

    # FIXME: le découpage fait ici ne marche qu'avec les restriction suposée
    # sur le fichier d'entrée, cad avec que:
    # - des nouveau node addr:housenumber ou place
    # - des nouvelle relations type=associatedStreet
    # - des ways extraits d'osm potentiellement modifiés
    # - des node extraits d'osm non modifiés

    # Cherche la relation associatedStreet de chaque nouveau node
    # addr:housenumber:
    associatedStreet_of_housenumber_node = {}
    for n in osm.nodes.itervalues():
        if n.id() < 0 :
            if "addr:housenumber" in n.tags:
                associatedStreet_of_housenumber_node[n.id()] = []
            else:
                assert(("place" in n.tags) or ("highway" in n.tags))
        else:
            # le code actuel ne sait partitionner que des neuds addr:housenumber que l'on a
            # créé nous même (id<0)
            # les autres on vas les zapper donc on vérifie qu'il
            # s'agit bien d'un noeuds déjà existant dans OSM (id >=0) et 
            # non modifié (pas d'attribut action)
            assert(n.id() >= 0 and "action" not in n.attrs)
    for r in osm.relations.itervalues():
        if r.id() < 0 and r.tags.get("type") == "associatedStreet":
            for mtype,mref,mrole in r.itermembers():
                if mtype == 'node':
                    associatedStreet_of_housenumber_node[mref].append(r)
        else:
            # le code actuel ne sait partitionner que les relation
            # associatedStreet que l'on a créé nous même (id<0)
            # les autres on vas les zapper donc on vérifie qu'il
            # s'agit bien de relation déjà existantt dans OSM (id >=0) et 
            # non modifié (pas d'attribut action)
            assert(r.id() >= 0 and "action" not in r.attrs)

    # Cree un fichier par relation associatedStreet:
    for r in osm.relations.itervalues():
        if r.id() < 0 and r.tags.get('type') == "associatedStreet":
            street_osm = Osm({})
            street_relation = Relation(r.attrs.copy(), r.tags.copy())
            street_osm.add_relation(street_relation)
            for mtype,mref,mrole in r.itermembers():
                if mrole  == 'house':
                    assert(mtype == 'node')
                    if len(associatedStreet_of_housenumber_node[mref]) == 1:
                        node = osm.nodes[mref]
                        street_osm.add_node(node)
                        street_relation.add_member(node, mrole)
                else:
                    street_relation.add_member_type_ref_role(mtype, mref, mrole)
            filename = subdir + to_ascii(r.tags['name']) + ".osm"
            filename_osm_map[filename] = street_osm
    # Partitionne les noeuds ambigus
    noeuds_ambigus = [osm.nodes[i] for i in associatedStreet_of_housenumber_node.iterkeys() if
        len(associatedStreet_of_housenumber_node[i]) > 1]
    filename_osm_map.update(partition_osm_nodes_filename_map(noeuds_ambigus, subdir + "_AMBIGUS_"))
    # Partitionne les noeuds orphelins
    noeuds_orphelins = [osm.nodes[i] for i in associatedStreet_of_housenumber_node.iterkeys() if
        len(associatedStreet_of_housenumber_node[i]) == 0]
    filename_osm_map.update(partition_osm_nodes_filename_map(noeuds_orphelins, subdir + "_ORPHELINS_"))

    # Avec l'intégration des addr:housenumber au buildings, le fichier d'entrée
    # contiens peut-être aussi des way issue d'OSM qui ont été modifiés.
    # On vas donc essayer de répartir ces ways dans le partitioning, mais
    # cela est possible que si le way est utilisé dans une seule partition (un
    # seul fichier) sinon cela génèrerais des conflits de version.
    filenames_of_new_nodes = {}
    for filename, new_osm in filename_osm_map.iteritems():
        for n in new_osm.nodes.itervalues():
            if n.id() < 0:
                if not n.id() in filenames_of_new_nodes:
                    filenames_of_new_nodes[n.id()] = set()
                filenames_of_new_nodes[n.id()].add(filename)
    for way in osm.ways.itervalues():
        assert(way.id() >= 0)
        if "action" in way.attrs:
            filenames_of_way = set()
            for nid in way.nodes:
                if nid < 0:
                    filenames_of_way.update(filenames_of_new_nodes[nid])
            if len(filenames_of_way) == 1:
                # Ajoute le way dans le seul fichier:
                way_new_osm = filename_osm_map[filenames_of_way.pop()]
                for nid in way.nodes:
                    if not nid in way_new_osm.nodes:
                        node = osm.nodes[nid]
                        way_new_osm.add_node(node)
                way_new_osm.add_way(way)
            elif len(filenames_of_way) > 1:
                # On ne duplique pas la version modifié du way
                # On rajoute donc un fixme vers ses neuds pour indiquer
                # qu'il faudrait les intégrer au way manuellement:
                for nid in way.nodes:
                    if nid<0:
                        node = osm.nodes[nid]
                        if "fixme" in node.tags:
                            node.tags["fixme"] += " et " + FIXME_JOINDRE_NOEUD_AU_WAY
                        else:
                            node.tags["fixme"] = FIXME_JOINDRE_NOEUD_AU_WAY

    zip_output = zipfile.ZipFile(zip_filename,"w", zipfile.ZIP_DEFLATED)
    for filename, osm in filename_osm_map.iteritems():
        s = StringIO()
        OsmWriter(osm).write_to_stream(s)
        zip_output.writestr(filename, s.getvalue())
    zip_output.close()

def partition_osm_lieuxdits_zip(osm_addresses, osm_lieuxdits, zip_filename, subdir=""):
    filename_osm_map = {}
    if subdir: subdir += "/"

    # FIXME: le découpage fait ici ne marche qu'avec les restriction suposée
    # sur le fichier osm_addresses d'entrée, cad avec que:
    # - des nouveau node addr:housenumber ou place
    # - des nouvelle relations type=associatedStreet
    # - des ways extraits d'osm potentiellement modifiés
    # - des node extraits d'osm non modifiés

    # Partitionne les noeuds de lieuxdits (place=*):
    noeuds_lieuxdits = [n for n in osm_addresses.nodes.itervalues()
        if (n.id()<0) and ("place" in n.tags)]
    osms_lieuxdits = partition_osm_nodes_filename_map(noeuds_lieuxdits,
        subdir + "lieux-dits")
    filename_osm_map.update(osms_lieuxdits)

    # Partitionne les noeuds de rue (highway=):
    noeuds_rues = [n for n in osm_addresses.nodes.itervalues() 
        if (n.id()<0) and ("highway" in n.tags)]
    osms_rues = partition_osm_nodes_filename_map(noeuds_rues,
        subdir + "lieux_ressemblants_noms_de_rues_-_NE_PAS_ENVOYER_SUR_OSM")
    for filename, new_osm in osms_rues.iteritems():
        new_osm.attrs["upload"] = "false"
    filename_osm_map.update(osms_rues)

    filename_osm_map[subdir + "limites_lieux-dits_-_NE_PAS_ENVOYER_SUR_OSM.osm"] = osm_lieuxdits

    zip_output = zipfile.ZipFile(zip_filename,"w", zipfile.ZIP_DEFLATED)
    for filename, osm in filename_osm_map.iteritems():
        s = StringIO()
        OsmWriter(osm).write_to_stream(s)
        zip_output.writestr(filename, s.getvalue())
    zip_output.writestr(subdir + "LISEZ-MOI.txt", """Bien verifier le nom et la position des lieux-dits.\r\nRemplir le tag place= en s'aidant des limites (nombre de maisons).\r\nAttention: les maisons avec numero d'adresse sont exclues des limites a tort et devraient souvent etre comptabilisees.\r\nhttp://wiki.openstreetmap.org/wiki/FR:Key:place\r\n""") 
    zip_output.close()
    
            


  
    

def cherche_osm_buildings_proches(code_departement, code_commune, osm, transform_to_osm, transform_from_osm):
    """ Cherche a intégrer les nœuds "addr:housenumber" du fichier
        d'entrée osm avec les building extraits de la base OSM.
    """
    sys.stdout.write((u"Intégration avec les buidings proches présent dans la base OSM.\n").encode("utf-8"))
    sys.stdout.write((u"Chargement des buidings\n").encode("utf-8"))
    sys.stdout.flush();
    buildings_osm = get_osm_buildings_and_barrier_ways(code_departement, code_commune)
    for node in itertools.chain.from_iterable(
            [o.nodes.itervalues() for o in [osm, buildings_osm]]):
        if not hasattr(node,'xy'):
            node.position = transform_from_osm((float(node.attrs["lon"]), float(node.attrs["lat"])))
    # créé un index spatial de tous les ways:
    ways_index = rtree.index.Index()
    for way in buildings_osm.ways.itervalues():
        if way.nodes[0] == way.nodes[-1]:
            way.shape = Polygon([buildings_osm.nodes[id].position for id in way.nodes])
        else:
            way.shape = LineString([buildings_osm.nodes[id].position for id in way.nodes])
        ways_index.insert(way.id(), way.shape.bounds, way.id())
    sys.stdout.write((u"Recherche des buiding proches\n").encode("utf-8"))
    sys.stdout.flush();
    for node in osm.nodes.values():
        if "addr:housenumber" in node.tags:
            x,y = node.position
            search_bounds = [x - MAX_BUILDING_DISTANCE_METERS, y - MAX_BUILDING_DISTANCE_METERS,
                             x + MAX_BUILDING_DISTANCE_METERS, y + MAX_BUILDING_DISTANCE_METERS]
            near_ways = [buildings_osm.ways[e.object] for e in ways_index.intersection(search_bounds, objects=True)]
            if  hasattr(node, 'limite_parcelle') and node.limite_parcelle != None:
                    #and node.liimite_parcelle.distance(node.position) < MAX_BUILDING_DISTANCE_METERS:
                # On connais les limites de la parcelle 
                # On vas donc filtrer les ways avec ceux qui sont contenus
                # dans la parcelle.
                # Pour déterminer les ways qui sont contenus dans la parcelle
                # avec un peut de marge, on vas faire l'union de deux
                # tests:
                # - les way qui sont strictement contenus dans les limites de
                #   parcelle étendue d'1m (afin de considérer par exemple les  
                #   barier qui sont en limite de parcelle)
                # - les way qui intersect les limites réduite d'1m de la parcelle
                #   (afin de prendre en comte aussi les buidings à cheval sur 
                #    une autre parcelle).
                limite_etendue = node.limite_parcelle.buffer(1)
                limite_reduite = node.limite_parcelle.buffer(-1)
                near_ways = filter(lambda way:
                    limite_reduite.intersects(way.shape) or
                        limite_etendue.contains(way.shape),
                    near_ways)

            # Les numéros déssinés sur le cadastre sont souvent orientés
            # vers la parcelle ou le building auquel il font référence
            # Si se n'est pas le cas il seront dessinés horizontalement.
            # Donc pour les numéros qui ne sont pas horizontal (angle < -2° ou > 2°)
            # on vas chercher à les projeter selon leur angle.
            # Sinon, sans angle, la projection sera faite orthogonalement.
            angle = None
            if hasattr(node, "angle") and node.angle != None:
                angle_deg = node.angle*180 / math.pi
                if angle_deg < -2 or angle_deg > 2:
                    # on projete perpandiculairement (on ajoute 90°=pi/2)
                    angle = node.angle + math.pi/2

            best_way, best_index, best_pos = nearest_intersection(node, near_ways, buildings_osm, angle)




            if best_way and node.position.distance(best_pos) < MAX_BUILDING_DISTANCE_METERS:
                # Il pourait en fait y avoir plusieurs ways qui contiennent le même segment, on vas tous les chercher
                # FIXME: il faudrait même chercher parmis les ways qui ne sont pas des building...
                a = best_way.nodes[best_index-1]
                b = best_way.nodes[best_index]
                p = Point(node.position)
                best_ways = []
                best_indexes = []
                node_inside_building = False
                for way in near_ways:
                    for i in xrange(len(way.nodes)-1):
                        if (way.nodes[i] == a and way.nodes[i+1] == b) \
                                or (way.nodes[i] == b and way.nodes[i+1] == a):
                            best_ways.append(way)
                            best_indexes.append(i+1)
                            if type(way.shape) == Polygon \
                                    and way.shape.contains(p) \
                                    and way.shape.boundary.distance(p) > NODE_INSIDE_BUILDING_DISTANCE_MARGIN:
                                node_inside_building = True

                # Si on a projeté selon l'angle du numéro, on vérifie qu'il n'y a pas trop d'incidence 
                # pour la projection, l'idéal étant bien sure une projection
                # orthogonale cad avec une incidence nulle. On autorise jusqu'à 30°(pi/6):
                a_xy = buildings_osm.nodes[a].position
                b_xy = buildings_osm.nodes[b].position
                trop_d_incidence = angle != None and incidence(a_xy, b_xy, angle) > (math.pi/6)

                # On intègre pas le numéro si il est à l'intérieur d'un building,
                # car sur le cadastre un numéro dessiné dans un building est forcément mal placé
                if (not node_inside_building) and (not trop_d_incidence):
                    # Comme on vas ajouter node a un way provenant du fichier buildings_osm, 
                    # pour garder buildings_osm cohérent, on ajoute aussi node à buildings_osm:
                    buildings_osm.add_node(node)
                    for best_way,best_index in zip(best_ways, best_indexes):
                        # On ajoute les best_way et ses nodes au fichier osm:
                        for id in best_way.nodes:
                            if not id in osm.nodes:
                                osm.add_node(buildings_osm.nodes[id])
                        if not best_way.id() in osm.ways:
                            osm.add_way(best_way)
                        # On insère node au best way a la position best_index:
                        best_way.attrs["action"] = "modify"
                        best_way.nodes.insert(best_index, node.id())
                    # On déplace node à la position best_pos:
                    node.position = best_pos
                    node.attrs["lon"], node.attrs["lat"] = map(str, transform_to_osm(best_pos))



