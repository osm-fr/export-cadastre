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

# Partitionne les noeuds d'un fichier osm en groupes de taille équivalente.

import math
from numpy import vstack
from scipy.cluster.vq import kmeans,vq

from .osm        import Osm,Node,Way,OsmWriter,Relation



# Taille du partitionnemens des noeus addr:housenumber qui sont orphelins
# (sans rue connue) ou ambigus (plus d'une rue possible)
TAILLE_PARTITIONEMENT_NOEUDS = 20


def partition_points(points, nb_partitions):
  """ Partitionnement de l'ensemble des points
      en utilisant K-means de la bibliothèque scipy
      retourne un tableau qui donne l'index de la partition de chaque point
  """
  # Génère une matrice à partire des points:
  data = vstack((points,))
  # Calcule des partitions K-means avec K=nb_clusters
  centroids,_ = kmeans(data, nb_partitions)
  # Affecte chaque points dans une partition:
  idx,_ = vq(data,centroids)
  return idx

def partition_osm_nodes(osm_nodes, taille_partitions):
  """  Partitionne une liste de noeuds osm en groupe de taille donnée.
       Retourne la liste des groupes.
  """
  try:
      # si on a gardé dans le champ xy la position des points dans la projection originale, on l'utilise:
      positions = [n.position for n in osm_nodes]
  except:
      # sinon on utilise lon,lat:
      positions = [(float(n.attrs["lon"]), float(n.attrs["lat"])) for n in osm_nodes]
  nb_partitions = int(len(osm_nodes) / taille_partitions)
  idx = partition_points(positions , nb_partitions)
  partitions = [[] for p in range(nb_partitions)]
  bboxes = [(float("inf"),float("inf"),float("-inf"),float("-inf")) for p in range(nb_partitions)]
  for n in range(len(osm_nodes)):
    p = idx[n]
    partitions[p].append(osm_nodes[n])
    bboxes[p] = tuple(min(*m) for m in zip(bboxes[p][:2],positions[n])) + tuple(max(*m) for m in zip(bboxes[p][2:],positions[n]))
  return list(zip(partitions, bboxes))


def partition_osm_nodes_filename_map(node_list, filenameprefix):
    """Partitionne les noeuds de la node list en plusieurs objet Osm()
       et retourne une map entre un nom de fichier et ces éléments Osm.
    """
    filename_osm_map = {}
    if len(node_list) > TAILLE_PARTITIONEMENT_NOEUDS:
        partitions = partition_osm_nodes(node_list , TAILLE_PARTITIONEMENT_NOEUDS)
        partitions = list(zip(*partitions))[0]
    else:
        partitions = [node_list]
    if len(partitions) > 1:
        taille_index = int(math.ceil(math.log10(len(partitions)+1)))
        for i in range(len(partitions)):
            osm = Osm({})
            for n in partitions[i]:
                osm.add_node(n)
            filename = filenameprefix + ("%%0%dd.osm" % taille_index) % (i+1,)
            filename_osm_map[filename] = osm
    elif len(partitions[0]) > 0:
        osm = Osm({})
        for n in partitions[0]:
            osm.add_node(n)
        filename_osm_map[filenameprefix + ".osm"] = osm
    return filename_osm_map


