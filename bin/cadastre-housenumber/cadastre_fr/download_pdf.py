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
Téléchargement des pdf depuis le cadastre (http://cadastre.gouv.fr)

Ce script est inspiré du programme Qadastre de Pierre Ducroquet
(https://gitorious.org/qadastre/qadastre2osm/)
et du script import-bati.sh
(http://svn.openstreetmap.org/applications/utils/cadastre-france/import-bati.sh)

"""

import re
import sys
import time
import os.path
import traceback
from shapely.geometry.polygon import Polygon

from .tools import write_string_to_file
from .tools import write_stream_to_file
from .tools import command_line_error
from .tools import download_cached
from .parser import CadastreParser
from .website import CadastreWebsite
from .website import command_line_open_cadastre_website
from .geometry import BoundingBox
from .transform import OSMToCadastreTransform
from .recognizer import LimitPathRecognizer


PDF_DOWNALOD_WAIT_SECONDS = 2
# Nombre de pixels / unite projection cadastre des PDF exportés
PDF_DOWNLOAD_PIXELS_RATIO = 4.5
# Mode de découpage des pdf: "NB": pour nombre fixe, "SIZE": pour taille fixe:
PDF_DOWNLOAD_SPLIT_MODE = "SIZE" 
# Si MODE="SIZE", Taille dans la projection cadastrale (~ mètres) des PDF exportés:
PDF_DOWNLOAD_SPLIT_SIZE = 200
# Si MODE="NB", nombre par lequelle la taille du pdf sera découpée (en
# largeur et en hauteur):
PDF_DOWNLOAD_SPLIT_NB = 2


def download_pdfs(cadastreWebsite, code_departement, code_commune, ratio=PDF_DOWNLOAD_PIXELS_RATIO, mode=PDF_DOWNLOAD_SPLIT_MODE, nb=PDF_DOWNLOAD_SPLIT_NB, size=PDF_DOWNLOAD_SPLIT_SIZE, wait=PDF_DOWNALOD_WAIT_SECONDS,force_bbox=None):
    """Download the pdfs from the cadastreWebsite and yield the filenames.
       Try to restrict the results to pdf representing bbox within city limit.
    """
    limitBboxFilterFunc = LimitBboxFilterFunc()
    for pdf_filename in download_pdfs_filter(cadastreWebsite, code_departement, code_commune, ratio, mode, nb, size, wait, force_bbox, limitBboxFilterFunc):
        limitBboxFilterFunc.feed_pdf(pdf_filename)
        yield pdf_filename

def download_pdfs_filter(cadastreWebsite, code_departement, code_commune, ratio, mode, nb, size, wait,force_bbox, bboxFilterFunc):
    """Download the pdfs from the cadastreWebsite and yield the filenames."""
    cadastreWebsite.set_departement(code_departement)
    cadastreWebsite.set_commune(code_commune)
    projection = cadastreWebsite.get_projection()
    bbox = cadastreWebsite.get_bbox()
    write_string_to_file(projection + ":%f,%f,%f,%f" % bbox, code_commune + ".bbox")
    if force_bbox:
        bbox = OSMToCadastreTransform(projection).transform_bbox(
            BoundingBox(*force_bbox))
    if mode=="SIZE":
        liste = decoupage_bbox_cadastre_size(bbox, size, ratio)
    else:
        liste = decoupage_bbox_cadastre_nb(bbox, nb, ratio)
    for ((i,j), sous_bbox, (largeur,hauteur)) in liste:
        if (bboxFilterFunc != None) and (not bboxFilterFunc(sous_bbox)):
            continue
        pdf_filename = code_commune + ("-%d-%d" % (i,j)) + ".pdf"
        bbox_filename = code_commune + ("-%d-%d" % (i,j)) + ".bbox"
        sous_bbox_str = projection + (":%f,%f,%f,%f" % sous_bbox)
        write_string_to_file(sous_bbox_str,  bbox_filename)
        open_function = lambda: cadastreWebsite.open_pdf(sous_bbox, largeur, hauteur)
        if download_cached(open_function, pdf_filename):
            time.sleep(wait)
        yield pdf_filename

def decoupage_bbox_cadastre_forced(bbox, nb_x, x_bbox_size, x_pixels_ratio, nb_y, y_bbox_size, y_pixels_ratio):
  sys.stderr.write((u"Découpe la bbox en %d * %d [%d pdfs]\n" % (nb_x,nb_y,nb_x*nb_y)).encode("utf-8"))
  sys.stderr.flush()
  xmin, ymin, xmax, ymax = bbox
  for i in xrange(nb_x):
    x1 = xmin + i * x_bbox_size
    x2 = min(x1 + x_bbox_size, xmax)
    largeur_px = int((x2-x1) * x_pixels_ratio)
    for j in xrange(nb_y):
      y1 = ymin + j * y_bbox_size
      y2 = min(y1 + y_bbox_size, ymax)
      hauteur_px = int((y2-y1) * y_pixels_ratio)
      yield ((i,j),(x1,y1,x2,y2),(largeur_px,hauteur_px))
      if (y2 == ymax): break
    if (x2 == xmax): break

def decoupage_bbox_cadastre_size(bbox, max_size, pixels_ratio):
  """Génère un découpage de la bbox en m*n sous bbox, de taille maximale
     (max_size, max_size)
     Retourne des tuples ( (i,j), sous_bbox, (largeur_px,hauteur_px) ) 
     correspondant à la sous bbox d'indice i,j dans le découpage m*n. 
     Cette sous bbox ayant une taille en pixels size*pixels_ratio
  """
  xmin,ymin,xmax,ymax = bbox
  assert(xmin < xmax)
  assert(ymin < ymax)
  xmin = xmin - 10
  xmax = xmax + 10
  ymin = ymin - 10
  ymax = ymax + 10
  nb_x = int((xmax - xmin - 1) / max_size) + 1
  nb_y = int((ymax - ymin - 1) / max_size) + 1
  return decoupage_bbox_cadastre_forced((xmin,ymin,xmax,ymax), nb_x, max_size, pixels_ratio, nb_y, max_size, pixels_ratio)

def decoupage_bbox_cadastre_nb(bbox, nb, pixels_ratio):
  """Génère un découpage de la bbox en nb*nb sous bbox, de taille moindre.
     Retourne des tuples ( (i,j), sous_bbox, (largeur_px,hauteur_px) ) 
     correspondant à la sous bbox d'indice i,j dans le découpage nb*nb. 
     Cette sous bbox ayant une taille en pixels size*pixels_ratio
  """
  xmin,ymin,xmax,ymax = bbox
  assert(xmin < xmax)
  assert(ymin < ymax)
  xmin = xmin - 10
  xmax = xmax + 10
  ymin = ymin - 10
  ymax = ymax + 10
  x_bbox_size = (xmax - xmin) / nb
  y_bbox_size = (ymax - ymin) / nb
  return decoupage_bbox_cadastre_forced((xmin,ymin,xmax,ymax), nb, x_bbox_size, pixels_ratio, nb, y_bbox_size, pixels_ratio)






class LimitBboxFilterFunc():
    """This class represent a function to be used as "bboxFilterFunc" argument for the
       download_pdf_filter() function.

       I will exclude bbox that are out of the city limits.

       As the city limits are initially unknown, this filter need to be fed with 
       the downloaded PDF so that the limits could be extracted, 
       and then the filter function updated.
    """
    def __init__(self):
        self.limit = None
        self.recognizer = LimitPathRecognizer()
        self.cadastre_parser = CadastreParser([self.recognizer.handle_path])

    def __call__(self, bbox):
        keepBbox = True
        if self.limit != None:
            try:
                xmin, ymin, xmax, ymax=  bbox
                bbox_poly = Polygon([(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)])
                keepBbox = self.limit.intersects(bbox_poly)
            except:
                traceback.print_exc()
                sys.stderr.write((u"ATTENTION: problème lors de la vérification des limites\n").encode("utf-8"))
        return keepBbox


    def feed_pdf(self, pdf_filename):
        if self.limit != None: 
            pass # Consider only the first PDF with limit data
        else:
            try:
                self.cadastre_parser.parse(pdf_filename)
                if len(self.recognizer.limit) > 0:
                    for linear_rings in self.recognizer.limit:
                        for ring in linear_rings:
                            polygon = Polygon(ring)
                            if self.limit == None:
                                self.limit = polygon
                            else:
                                self.limit = self.limit.union(polygon)
            except:
                traceback.print_exc()
                sys.stderr.write((u"ATTENTION: problème lors de la détection des limites\n").encode("utf-8"))


