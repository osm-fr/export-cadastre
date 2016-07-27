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
Reconnaisseur de Path extrait des PDF du cadastre, pour pouvoir identifier:
 - des limites de parcelles
 - des maisons
 - des numéros de rues
 - des noms de lieux-dits
"""

import re
import sys
import math
import os.path
import xml.etree.ElementTree as ET

from cadastre_fr.geometry import Path
from cadastre_fr.tools import print_flush
from cadastre_fr.tools import toposort


TEXT_PATH_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "text_path_recognizer")
REFERENCE_STREET_NAME = os.path.join(TEXT_PATH_DATA_DIR , "reference-noms_de_rue.svg")
REFERENCE_LIEUXDITS = os.path.join(TEXT_PATH_DATA_DIR , "reference-noms_de_lieux-dits.svg")
REFERENCE_HOUSENUMBERS = os.path.join(TEXT_PATH_DATA_DIR , "reference-housenumbers.svg")


# distance max en mètres pour considérer qu'un polygon est fermé:
TOLERANFCE_FERMETURE_POLYGON_METRES = 0.5


class PathRecognizer(object):
    def handle_path(self, path, transform):
        return False

class LinesPathRecognizer(PathRecognizer):
    commands_re = re.compile("^(MLLLL*Z)+$")
    def __init__(self, name_closed_styletest_list):
        self.name_closed_styletest_list = name_closed_styletest_list
        for name, foo, bar in name_closed_styletest_list: 
            setattr(self, name, [])
    def handle_path(self, path, transform):
        if LinesPathRecognizer.commands_re.match(path.commands) and path.style:
            style = dict([v.split(':') for v in path.style.split(';')])
            for name, closed, styletest in self.name_closed_styletest_list:
                if styletest(style):
                    points = map(transform, path.points)
                    linear_rings = []
                    for commands_ring in path.commands[:-1].split('Z'):
                        first = points[0]
                        last = points[len(commands_ring)-1]
                        if closed and (first.distance(last) > TOLERANFCE_FERMETURE_POLYGON_METRES):
                            # Ce n'est pas un polygone fermé mais une ligne brisée.
                            break
                        linear_rings.append(points[:len(commands_ring)])
                        points = points[len(commands_ring):]
                    if len(linear_rings) > 0:
                        getattr(self, name).append(linear_rings)
                        return True
        return False


PARCEL_LINE_PATH_RECOGNIZER = [
        ['parcels', True, lambda style: 
            style.has_key('stroke-width') and
            (float(style["stroke-width"]) > 0.7) and
            (float(style["stroke-width"]) < 0.8) and
            (style.get('fill') == "none") and 
            (style.get('stroke') == "#000000") and 
            (style.get('stroke-opacity') == "1") and 
            (style.get('stroke-dasharray') == "none")
        ]
    ]
BUILDING_LINE_PATH_RECOGNIZER = [
        ['buildings',       True, lambda style: style.get('fill') == "#ffcc33"],
        ['light_buildings', True, lambda style: style.get('fill') == "#ffe599"]
    ]

WATER_LINE_PATH_RECOGNIZER = [
        ['waters',     True, lambda style: style.get('fill') == "#98c3d9"],
        ['riverbanks', True, lambda style: style.get('fill') == "#1979ac"]
    ]

LIMIT_LINE_PATH_RECOGNIZER = [
        ['limit', False, lambda style: 
            (style.get('fill') == "none") and
            (style.get('stroke') == "#ffffff") and
            (style.get('stroke-opacity') == "1") and
            (style.get('stroke-dasharray') == "none") and
            style.has_key('stroke-width') and
            (((float(style["stroke-width"]) > 17.8) and (float(style["stroke-width"]) < 17.9))
             or
             ((float(style["stroke-width"]) > 8.4) and (float(style["stroke-width"]) < 8.6)))
        ]
    ]

class ParcelPathRecognizer(LinesPathRecognizer):
    def __init__(self):
        LinesPathRecognizer.__init__(self, PARCEL_LINE_PATH_RECOGNIZER)

class BuildingPathRecognizer(LinesPathRecognizer):
    def __init__(self):
        LinesPathRecognizer.__init__(self, BUILDING_LINE_PATH_RECOGNIZER)

class WaterPathRecognizer(LinesPathRecognizer):
    def __init__(self):
        LinesPathRecognizer.__init__(self, WATER_LINE_PATH_RECOGNIZER)

class LimitPathRecognizer(LinesPathRecognizer):
    def __init__(self):
        LinesPathRecognizer.__init__(self, LIMIT_LINE_PATH_RECOGNIZER)

class StandardPathRecognizer(LinesPathRecognizer):
    def __init__(self):
        LinesPathRecognizer.__init__(self, 
                BUILDING_LINE_PATH_RECOGNIZER + LIMIT_LINE_PATH_RECOGNIZER + WATER_LINE_PATH_RECOGNIZER)

class NamePathRecognizer(PathRecognizer):
    def __init__(self):
        self.street_name_recognizer = TextPathRecognizer(tolerance=0.05, min_scale=0.9, max_scale=1.1)
        self.street_name_recognizer.load_from_svg(REFERENCE_STREET_NAME)
        self.lieuxdits_recognizer = TextPathRecognizer(tolerance=0.05, min_scale=0.9, max_scale=1.1, force_horizontal=True)
        self.lieuxdits_recognizer.load_from_svg(REFERENCE_LIEUXDITS)
        # Il y a parfois des noms écrits en petit, pour les des lotissement par exemple, on réutilise
        # la même base de donnée utilisée pour les nom de rues mais en diminuant la taille (scale):
        self.small_name_recognizer = TextPathRecognizer(tolerance=0.05, min_scale=0.55, max_scale=0.69, force_horizontal=False)
        self.small_name_recognizer.database = self.street_name_recognizer.database
        self.small_name_recognizer.space_width = self.street_name_recognizer.space_width * (self.small_name_recognizer.max_scale + self.small_name_recognizer.min_scale) / (self.street_name_recognizer.max_scale + self.street_name_recognizer.min_scale)
        self.street_names = []
        self.small_names = []
        self.lieuxdits = []
    def handle_path(self, path, transform):
        for recognizer, liste in [
                (self.lieuxdits_recognizer, self.lieuxdits),
                (self.small_name_recognizer, self.small_names),
                (self.street_name_recognizer, self.street_names)]:
            found = recognizer.recognize(path)
            if found:
                text, position, angle = found
                # On rejette les mots commencant par un chiffre:
                if not ord(text[0]) in range(ord('0'), ord('9')+1):
                    liste.append((text, transform(position), angle))
                    if text.find("???") == -1: 
                        return True
        return False        


class TextPathRecognizer(PathRecognizer):
    __slots__ = ('database', 'tolerance', 'min_scale', 'max_scale', 'styles', 'force_horizontal', 'angle_tolerance_deg', 'space_width')
    def __init__(self, tolerance, min_scale, max_scale, styles=[], force_horizontal = False, angle_tolerance_deg = 5):
        self.database = {}
        self.tolerance = tolerance
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.styles = styles
        self.force_horizontal = force_horizontal
        self.angle_tolerance_deg = angle_tolerance_deg 
        self.space_width = None
    def add(self, value, path, alternatives=[]):
        # On utilise le début de la commande du path comme 
        # index de la database:
        idx = path.commands[:path.commands.index('Z')]
        if not idx in self.database:
            self.database[idx] = []
        self.database[idx].append((value, path, alternatives))
    def save_to_svg(self, filename):
        f = open(filename,"w")
        f.write("""<?xml version="1.0"?>\n<svg
          xmlns="http://www.w3.org/2000/svg"
          xml:space="preserve"
          xmlns:svg="http://www.w3.org/2000/svg"
          height="1052.5"
          width="1488.75"
          version="1.1">
        """)
        f.write(u"<!-- inversion de l'axe Y pour remettre à l'endroit:\n<g transform='matrix(1,0,0,-1,0,0)'>-->\n".encode("utf-8"))
        for elems in self.database.itervalues():
            for value, path, _ in elems:
                f.write('    <path style="fill:#000000;fill-opacity:1;fill-rule:nonzero;stroke:none"\n d="')
                f.write(path.d)
                f.write('">\n')
                f.write("        <title>" + value + "</title>\n")
                f.write("    </path>\n")
        f.write("<!--</g>-->\n")
        f.write("</svg>\n")
        f.close()
    def load_from_svg(self, filename):
        """Charge les paths de référence pour la reconnaissance depuis un fichier SVG.
           La valeur associée à reconnaître est stockée dans le titre des paths."""
        root = ET.parse(filename).getroot()
        elems = []
        #print_flush((u"#Charge les path: " + os.path.basename(filename) + "\n"))
        for p in root.iter('{http://www.w3.org/2000/svg}path'):
            # La valeur à reconnaître pour le path est stockée dans le titre:
            title = p.find('{http://www.w3.org/2000/svg}title')
            if title != None:
                elems.append((title.text, Path.from_svg(p.get('d'))))
        if len(elems) == 0:
            raise Exception("Aucun path avec un titre (<title>) dans le fichier " + filename)
        # La façon de reconnaître le texte contenu dans un path consiste à
        # comparer le début du path avec chacun des éléments de référence
        # conterus dans la database jusqu'à en trouver un qui correspond,
        # puis reconnaître la suite du path.
        # Pour certains caratère, comme ceux avec accents (ex: é) le
        # début du path vas être le même que la version sans sans accent
        # (ex: e) donc il est important de comparer d'abord avec la version
        # la plus complexe des path pour reconnaître é avant e, sans quoi
        # un fois reconnus e, l'accent tout seul qui suit ne serait pas
        # reconnu.
        # On utilise un tri topologique pour prendre en compte ces dépendances.
        # Mais il y a un autre problème à traiter: celui des caractrès
        # différents qui sont représentés par un même path éqvivalent mais
        # avec un angle différent, c'est le cas du carctère u qui est un n
        # à l'envers ou de p et d.  On ne peut pas trier ces cas là (car
        # c'est une dépendance circulaire) mais on vas les traiter de
        # façon particulière, en enregistrant pour chacun d'eux la liste
        # des alternatives possibles qu'il faudra potentiellement 
        # considérer si on l'a reconnu.
        deps = { i:set() for i in xrange(len(elems))} 
        alternatives = [set() for i in xrange(len(elems))]
        for i in xrange(len(elems)-1):
          value_i, path_i = elems[i]
          for j in xrange(i+1,len(elems)):
            value_j, path_j = elems[j]
            if value_i != value_j:
                i_startswith_j = path_i.startswith(path_j, tolerance = self.tolerance, min_scale=self.min_scale, max_scale=self.max_scale)
                j_startswith_i = path_j.startswith(path_i, tolerance = self.tolerance, min_scale=self.min_scale, max_scale=self.max_scale)
                if i_startswith_j:
                    if j_startswith_i:
                      #alternatives[i].add(j)
                      #alternatives[j].add(i)
                      angle_deg = abs(int(round(i_startswith_j*180/math.pi)))
                      #print_flush(u"#caractère %s ~(%d°) %s\n" % (value_i, (angle_deg/2)*2, value_j))
                      if angle_deg < self.angle_tolerance_deg:
                            alternatives[i].add(j)
                      #if angle_deg < 5:
                      #    for v,p in [(value_i,path_i), (value_j,path_j)]:
                      #        print "  - %s  : p0_distance : %f" %(v, p.p0_distance())
                      #        print "         len(points) : %d" % len(p.points)
                      #        print "         l2 / l1 = %f" % rapport_l2_sur_l1(p)
                      #        #print str([(p.points[i][0]-p.points[i-1][0], p.points[i][1]-p.points[i-1][1]) for i in xrange(1, len(p.points))])
                    else:
                        #print_flush(value_i + " commence par " + value_j + "\n")
                        deps[j].add(i)
                elif j_startswith_i:
                    #print_flush(value_j + " commence par " + value_i + "\n")
                    deps[i].add(j)
        for i in toposort(deps):
            val, path = elems[i]
            alters = [elems[j] for j in alternatives[i]]
            self.add(val, path, alters)
        # Calcule la distance d'un espace comme la moité de la largeur moyenne des caractères:
        # en considérant que les caractères sont horizontal (angle = 0)
        largeur_moyenne = sum([largeur_path(0, path) for value,path in elems]) / len(elems)
        self.space_width = largeur_moyenne / 2
        #print "Largeur espaces = " + str(self.space_width)

    def recognize(self, path):
        if self.styles:
            path_styles = path.style.split(';')
            for s in self.styles:
                if not s in path_styles: return None
        original_path = path
        result = ""
        if self.force_horizontal:
            original_angle = 0.0
        else:
            original_angle = None
        previous_position = None
        while len(path.points):
            found = False
            idx = path.commands[:path.commands.find('Z')]
            if idx in self.database:
                for value, compare_path, alternatives in self.database[idx]:
                    startswith = path.startswith(compare_path, tolerance=self.tolerance, min_scale=self.min_scale, max_scale=self.max_scale)
                    if startswith:
                        angle = startswith
                        if original_angle != None:
                            diff_angle = abs(angle - original_angle) 
                            if diff_angle > math.pi:
                                diff_angle = abs(2*math.pi - diff_angle)
                            if (diff_angle * 180 / math.pi) > self.angle_tolerance_deg:
                                # Ce caractère est reconu mais pas avec le bon angle, on passe 
                                continue
                        else:
                            # Le premier caractère du path déterminera l'angle du mot
                            # PB: traiter les alternatives (par exemple un mot qui commence par u OU n il faut considérer les deux possibilitées,
                            # qui peuvent ếtre déterminer par l'angle.
                            # Au lieux d'analyser toutes les alternatives, on vérifie que la positions du point suivant dans le path sera bien
                            # en avant par rapport au caractère considéré courant.
                            # FIXME: il faudrait mieux analyser toutes les alternatives possibles et renvoyer la liste de celle qui on reconnu tout le path
                            positions = projections_points(angle,  path.points[:len(compare_path.points)])
                            if len(path.points) > len(compare_path.points):
                                mean_cur_position = sum(positions)/len(positions)
                                next_point_position = projection_point(angle, path.points[len(compare_path.points)])
                                if next_point_position < mean_cur_position:
                                    #print_flush(u"caractère rejeté: " + value + "\n")
                                    # Le caractère suivant serait dérrière, on a pas du choisir le bon angle, c'est à dire 
                                    # le bon caractère à reconnaître, on continue pour en chercher un autre:
                                    continue
                            original_angle = angle
                            #result = result + "angle(%.2f)" % (original_angle*180/math.pi)
                        if len(alternatives):
                            # Il y a des alternatives pour ce caractère, on vas utiliser le rapport_l2_l1 pour les
                            # départager
                            # NOTE: cela est fait en pratique uniquement pour distinguer le l minuscule du I majuscule
                            cur_rapport_l2_sur_l1 = rapport_l2_sur_l1(path)
                            compare_raport_l1_l2 = rapport_l2_sur_l1(compare_path)
                            for alt_value, alt_path in alternatives:
                                alt_rapport_l2_sur_l1 = rapport_l2_sur_l1(alt_path)
                                if abs(cur_rapport_l2_sur_l1-alt_rapport_l2_sur_l1) < abs(cur_rapport_l2_sur_l1-compare_raport_l1_l2):
                                    value = alt_value
                                    compare_raport_l1_l2 = alt_rapport_l2_sur_l1
                        # Calcule de la position des points por déterminer si il y a un espace
                        positions = projections_points(original_angle,  path.points[:len(compare_path.points)])
                        if previous_position != None:
                            distance = min(positions) - previous_position
                        else:
                            distance = 0
                        previous_position = max(positions)
                        #result = result + "loc[%.2f,%.2f] pos[%.2f .. %.2f]" % (path.points[0][0], path.points[0][1], min(positions), max(positions))
                        #result = result + (" distance(%.2f)" % distance)
                        if distance > self.space_width:
                            result = result + " "
                        result = result + value 
                        #result = result + ("(%.1f)" % (angle*180/math.pi))
                        # Maintenant on traite la suite du path:
                        path = Path(
                            path.commands[len(compare_path.commands):],
                            path.points[len(compare_path.points):])
                        found = True
                        break;
            if not found:
                break
        if result:
            if len(path.points):
                # On a pas tout reconnu
                result += "???"
            position = original_path.bbox().center()
            return result, position, original_angle
        else:
            return None

class HousenumberPathRecognizer(TextPathRecognizer):
    def __init__(self):
        TextPathRecognizer.__init__(self, tolerance=0.05, min_scale=0.8, max_scale=1.2, styles=["fill:#000000"])
        self.load_from_svg(REFERENCE_HOUSENUMBERS)
        self.housenumbers = []
    def handle_path(self, path, transform):
        found = self.recognize(path)
        if found:
            text, position, angle = found
            if text[0] in ["1","2","3","4","5","6","7","8","9"]:
                self.housenumbers.append((text, transform(position), angle))
                return text.find("???") == -1
        return False


def projection_point(angle, point):
    return math.cos(angle) * point[0] + math.sin(angle) * point[1]

def projections_points(angle, points):
    cosa = math.cos(angle)
    sina = math.sin(angle)
    return [cosa*p[0] + sina * p[1] for p in points]

def largeur_path(angle, path):
    positions = projections_points(angle, path.points)
    return max(positions) - min(positions)

def rapport_l2_sur_l1(path):
    """ Calcule le rapport entre le premier et le deuxième segment du path.
        Cela est utilisé en pratique pour distinguer le l minuscule du 
        I majuscule
    """
    def distance((x1,y1),(x2,y2)):
        return math.sqrt((x2-x1)*(x2-x1)+(y2-y1)*(y2-y1))
    l1 = distance(path.points[0], path.points[1])
    l2 = distance(path.points[1], path.points[2])
    return  l2 / l1
