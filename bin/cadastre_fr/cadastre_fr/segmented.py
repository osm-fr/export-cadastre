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
Détection de bâtiment segmenté (fractionés) par le cadastre
(le plus souvent à cause de limites de parcelles).


Prend en entrée des fichiers osm contenant des bâtiments (buildings) avec
un tag "segmented" contenant des valeurs égales pour les buildings à fusionner,
ou rien ou "segmented"="no" pour ceux à ne pas fusioner,
et "segmented"="?" pour ceux pour lequel c'est ambigue.

De tels fichiers d'entrée peuvent être générés par le programme
segmented_building_find_joined.py

La sortie de ce programme est la gérération de deux fichiers
    scaler.pickle
    classifier.pickle
dump d'une instance de Scaler pour mettre à l'échelle les valeurs
et d'un classifier pour prédire à partir de ces valeurs
deux bâtiments fractionnés.

Les valeurs (features) d'un couple de bâtiment doivent être obtenus
en appelant la fonction
    fr_cadastre_segmented.get_classifier_vector_from_wkt(wkt1, wkt2)


Plusieurs classifiers ont été expérimentés.

 - KNeighborsClassifier
   meilleur équilibre entre nombre de correcte / faux négatifs / faux positifs.
   (peut être car on a beaucoup plus de données d'apperntissage négatives, il faudrait jouer sur les weight pour rééquilibrer)
   meilleurs résultats avec
    MinMaxScaler()
    KNeighborsClassifier(weights="distance", k = 8)
   La grid search cross validation donne k=4 mais en fait avec k=8 c'est bien mieux.


 - DecisionTreeClassifier
    peu de manqués (faux négatifs), mais beaucoup de faux positifs
    je ne sais pas utiliser Scaler améliore vraiment ou pas.

 - SVM
    peu de faux positifs, mais beaucoup de faux négatifs (manqués).
    meilleurs résultats avec:
        MinMaxScaler()
        SVC(kernel="rbf",C=500 ou plus, gamma=0.05)

 - SGDClassifier
    mauvais résultats

"""


import re
import sys
import copy
import math
import pickle
import numpy as np
import os.path
import operator
import itertools
#import tensorflow
import rtree.index
import sklearn
from sklearn import svm
from sklearn import tree
from sklearn import neighbors
sklearn_version = tuple(map(int, sklearn.__version__.split(".")[0:2]))
if sklearn_version  >= (0, 18):
    from sklearn.model_selection import GridSearchCV
else:
    from sklearn.grid_search import GridSearchCV
from sklearn import preprocessing
from functools import reduce
from shapely.geometry.polygon import Polygon

from .osm        import Osm,Node,Way,Relation,OsmParser,OsmWriter
from .transform  import get_centered_metric_equirectangular_transformation_from_osm
from .simplify   import simplify
from .tools      import iteritems, itervalues, iterkeys

# Import from ../cadastre_fr_segmented native object code
# which make should install in $HOME/.local/.lib/python3.X/site-package/:
from cadastre_fr_segmented import  get_classifier_vector_from_wkt
from cadastre_fr_segmented import  get_classifier_vector_from_coords


SEGMENTED_DATA_DIR =  os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data", "segmented_building")


def pickle_extension():
    if sys.version_info > (3, 0):
        ext = ".pickle3"
    else:
        ext = ".pickle2"
    return ext


def load_classifier_and_scaler():
    os.system("cd " + SEGMENTED_DATA_DIR  +"; make -s")
    ext = pickle_extension()
    classifier = pickle.load(open(os.path.join(SEGMENTED_DATA_DIR, "classifier" + ext), "rb"))
    scaler = pickle.load(open(os.path.join(SEGMENTED_DATA_DIR, "scaler" + ext), "rb"))
    return classifier, scaler


def get_predicted_segmented_buildings(classifier, scaler, osm_data):
    segmented_buildings_couples = []
    for building in get_buildings_ways(osm_data):
        for way in iter_contigous_ways(osm_data, building):
            if way.isBuilding and way.hasWall == building.hasWall and way.id() > building.id():
                if predict_segmented(classifier, scaler, osm_data, building, way):
                    segmented_buildings_couples.append( (building, way) )
    return segmented_buildings_couples


def iter_contigous_ways(osm_data, way):
    way_id = way.id()
    nodes = [osm_data.nodes[i] for i in way.nodes]
    contiguous_id = reduce(operator.or_, [node.ways for node in nodes], set())
    for i in contiguous_id:
        if i != way_id:
            yield osm_data.ways[i]

#def normalize_vector(vector):
#    if vector != None:
#        return map(lambda v, minn, maxx: (v - minn) / (maxx-minn), vector, min_segmented_analysis_vector, max_segmented_analysis_vector)
#    else:
#        return None

def predict_segmented(classifier, scaler, osm_data, way1, way2):
    vector1 = get_segmented_analysis_vector_from_osm(osm_data, way1, way2)
    vector2 = get_segmented_analysis_vector_from_osm(osm_data, way2, way1)
    if not vector1 is None:
        vector1 = [vector1]
        if not scaler is None:
            vector1 = scaler.transform(vector1)
    if not vector2 is None:
        vector2 = [vector2]
        if not scaler is None:
            vector2 = scaler.transform(vector2)
    return ((not vector1 is None) and classifier.predict(vector1) == [1]) or \
       ((not vector2 is None) and classifier.predict(vector2) == [1])


def test_classifier(classifier, scaler, osm_data):
    false_osm = Osm({'upload':'false'})
    missed_osm = Osm({'upload':'false'})
    nb_ok = 0
    nb_false = 0
    nb_missed = 0
    for building in get_buildings_ways(osm_data):
        for way in iter_contigous_ways(osm_data, building):
            if way.isBuilding and way.hasWall == building.hasWall and way.id() > building.id():
                areSegmented = building.isSegmented and (building.tags.get("segmented") == way.tags.get("segmented"))
                incertain = (building.tags.get("segmented") == "?") or (way.tags.get("segmented") == "?")
                if predict_segmented(classifier, scaler, osm_data, building, way):
                    if areSegmented:
                        #sys.stdout.write("o");sys.stdout.flush()
                        nb_ok = nb_ok + 1
                    elif not incertain:
                        #sys.stdout.write("F");sys.stdout.flush()
                        nb_false = nb_false + 1
                        add_way_to_other_osm(osm_data, building, false_osm)
                        add_way_to_other_osm(osm_data, way, false_osm)
                else:
                    if areSegmented:
                        #sys.stdout.write("M");sys.stdout.flush()
                        nb_missed = nb_missed + 1
                        add_way_to_other_osm(osm_data, building, missed_osm)
                        add_way_to_other_osm(osm_data, way, missed_osm)
    return nb_ok, nb_missed, nb_false, missed_osm, false_osm


def add_way_to_other_osm(source_osm, way, other_osm):
    if way.id() not in other_osm.ways:
        other_osm.add_way(way)
        for node_id in way.nodes:
            if not node_id in other_osm.nodes:
                node = source_osm.nodes[node_id]
                other_osm.add_node(node)



def get_buildings_ways(osm_data):
    result = []
    for way in itervalues(osm_data.ways):
        if way.isBuilding:
            way.isSegmented = way.tags.get("segmented") not in (None, "?", "no")
            way.hasWall = way.tags.get("wall") != "no" # default (None) is yes
            result.append(way)
    for rel in itervalues(osm_data.relations):
        if rel.isBuilding:
            rel.isSegmented = rel.tags.get("segmented") not in (None, "?", "no")
            rel.hasWall = rel.tags.get("wall") != "no" # default (None) is yes
            for item, role in osm_data.iter_relation_members(rel):
                if item != None: # not downloaded
                    if role in ("inner", "outer"):
                        item.hasWall = rel.hasWall
                        item.isSegmented = rel.isSegmented
                        if "segmented" in rel.tags:
                            item.tags["segmented"] = rel.tags["segmented"]
                        result.append(item)
    return result


def filter_buildings_junction(osm_data, buildings_couples):
    osm = Osm({'upload':'false'})
    for b1, b2 in buildings_couples:
        external1, common, external2 = get_external1_common_external2_ways(b1.nodes, b2.nodes)
        for node_id in common:
            node = osm_data.nodes[node_id]
            node.tags["fixme"] = "Est-ce que les bâtiments ne sont pas segmentés ici par le cadastre ?"
            if node_id not in osm.nodes:
                osm.add_node(node)
        way = Way({})
        way.nodes = common
        way.tags["name"] = "Est-ce que les bâtiments ne sont pas segmentés ici par le cadastre ?"
        osm.add_way(way)
    return osm


def find_joined_and_unmodified_buildings(segmented_osm, corrected_osm, tolerance):
    """Find buildings from segmented_osm osm representation that
       have either been joined or unmodified in corrected_osm
       Modify segmented_osm by adding a tag "segmented" to the building with the value
            "no" or "?", or the id in corrected_osm in which they are joined.
       Return the list of joined and unmodified buildings.
    """
    for cadastre_way in itertools.chain(itervalues(segmented_osm.ways), itervalues(segmented_osm.relations)):
        cadastre_way.isSegmented = False
    inputTransform, outputTransform = get_centered_metric_equirectangular_transformation_from_osm(segmented_osm)
    compute_transformed_position_and_annotate(segmented_osm, inputTransform)
    compute_transformed_position_and_annotate(corrected_osm, inputTransform)
    compute_buildings_polygons_and_rtree(segmented_osm, tolerance)
    compute_buildings_polygons_and_rtree(corrected_osm, tolerance)
    segmented_rtree = segmented_osm.buildings_rtree
    corrected_rtree = corrected_osm.buildings_rtree
    joined_buildings = []
    unmodified_buildings = []
    for segmented_way in itertools.chain(itervalues(segmented_osm.ways), itervalues(segmented_osm.relations)):
        if segmented_way.isBuilding and ("segmented" not in segmented_way.tags):
            segmented_way.tags["segmented"] = "?"
            for corrected_way in [corrected_osm.get(e.object) for e in corrected_rtree.intersection(segmented_way.bbox, objects=True)]:
                if corrected_way.isBuilding:
                    if ways_equals(segmented_way, corrected_way, tolerance):
                        unmodified_buildings.append(segmented_way)
                        segmented_way.tags["segmented"] = "no"
                    elif corrected_way.tolerance_polygon.contains(segmented_way.polygon):
                        composed_tolerance_polygon = segmented_way.tolerance_polygon
                        composed_ways = [segmented_way]
                        for segmented_way2 in [segmented_osm.get(e.object) for e in segmented_rtree.intersection(corrected_way.bbox, objects=True)]:
                            if segmented_way.tags.get("wall") == segmented_way2.tags.get("wall"):
                              if corrected_way.tolerance_polygon.contains(segmented_way2.polygon):
                                composed_tolerance_polygon = composed_tolerance_polygon.union(segmented_way2.tolerance_polygon)
                                composed_ways.append(segmented_way2)
                        if composed_tolerance_polygon.contains(corrected_way.polygon):
                            joined_buildings.append(composed_ways)
                            for way in composed_ways:
                                way.tags["segmented"] = corrected_way.textid()
                                way.isSegmented = True
    return joined_buildings, unmodified_buildings


def compute_transformed_position_and_annotate(osm_data, transform):
    for node in itervalues(osm_data.nodes):
        node.ways = set()
        node.relations = set()
        node.position = transform.transform_point(
            (node.lon(), node.lat()))
    for way in itervalues(osm_data.ways):
        way.relations = set()
    for rel in itervalues(osm_data.relations):
        rel.relations = set()
    for rel in itervalues(osm_data.relations):
       for rtype,rref,rrole in rel.itermembers():
          if rtype == "way":
              if rref in osm_data.ways:
                osm_data.ways[rref].relations.add(rel.id())
          if rtype == "node":
              if rref in osm_data.nodes:
                osm_data.nodes[rref].relations.add(rel.id())
          if rtype == "relation":
              if rref in osm_data.relations:
                osm_data.relations[rref].relations.add(rel.id())
    for way in itervalues(osm_data.ways):
        for node_id in way.nodes:
            node = osm_data.nodes[node_id]
            node.ways.add(way.id())
        way.isBuilding = way.tags.get("building") not in (None, "no")
        if way.isBuilding:
            way.hasWall = way.tags.get("wall") != "no" # default (None) is yes
    for rel in itervalues(osm_data.relations):
        rel.isBuilding = (rel.tags.get("type") == "multipolygon") and (rel.tags.get("building") not in (None, "no"))
        if rel.isBuilding:
            rel.hasWall = rel.tags.get("wall") != "no" # default (None) is yes

def compute_buildings_polygons_and_rtree(osm_data, tolerance):
    buildings_rtree = rtree.index.Index()
    osm_data.buildings_rtree = buildings_rtree
    for way in itervalues(osm_data.ways):
        if way.isBuilding:
            if len(way.nodes) >= 3:
               way.polygon = Polygon([osm_data.nodes[i].position for i in way.nodes])
            else:
               way.polygon = LineString([osm_data.nodes[i].position for i in way.nodes])
            way.bbox = way.polygon.bounds
            way.tolerance_polygon = way.polygon.buffer(tolerance)
            buildings_rtree.insert(way.id(), way.bbox, way.textid())
    for rel in itervalues(osm_data.relations):
        if rel.isBuilding:
            exterior = None
            interiors = []
            for rtype,rref,rrole in rel.itermembers():
                if rtype == "way":
                    way = osm_data.ways[rref]
                    if rrole == "outer":
                        exterior = [osm_data.nodes[i].position for i in way.nodes]
                    elif rrole == "inner":
                        interiors.append([osm_data.nodes[i].position for i in way.nodes])
            rel.polygon = Polygon(exterior, interiors)
            rel.bbox = rel.polygon.bounds
            rel.tolerance_polygon = rel.polygon.buffer(tolerance)
            buildings_rtree.insert(rel.id(), rel.bbox, rel.textid())


def ways_equals(way1, way2, tolerance):
    bbox_diff = max(list(map(abs, list(map(operator.sub, way1.bbox, way2.bbox)))))
    return (bbox_diff < tolerance) and \
        way1.tolerance_polygon.contains(way2.polygon) and \
        way2.tolerance_polygon.contains(way1.polygon)


def train(data, result, scoring=None):
    #scaler, classifier = train_svm(all_data, all_result, scoring)
    #scaler, classifier = train_tree(all_data, all_result, scoring)
    #scaler, classifier = train_sgd(all_data, all_result, scoring)
    scaler, classifier = train_kneighbors(data, result, scoring)
    return scaler, classifier


def train_kneighbors(data, result, scoring=None):
    print(("train KNeighborsClassifier {}".format(len(data))))
    #scaler = None
    scaler = preprocessing.MinMaxScaler()
    print(("Scale: {}".format(type(scaler))))
    if scaler != None:
        data = scaler.fit_transform(data)

    #classifier = neighbors.KNeighborsClassifier(weights = 'distance', n_neighbors=8)
    classifier = neighbors.KNeighborsClassifier(weights = 'distance', n_neighbors=6)
    classifier.fit(data, result)


    # GridSearchCV says best is with n_neighbors=4, but my observations show that n_neighbors=8 is way better.

    return scaler, classifier

    #parameters = {
    #    'weights': ('uniform', 'distance'),
    #    'n_neighbors': (8,) #range(3,11)
    #}
    #print(parameters)
    #search = GridSearchCV(neighbors.KNeighborsClassifier(), parameters, scoring=scoring, n_jobs=1)
    #search.fit(data, result)
    #print("best params: {}".format(search.best_params_))
    #print("best score: {}".format(search.best_score_))
    ##print
    #return scaler, search.best_estimator_.fit(data,result)


def train_tree(data, result, scoring=None):
    print(("train DecisionTreeClassifier {}".format(len(data))))
    scaler = None
    scaler = preprocessing.MinMaxScaler()
    print(("Scale: {}".format(type(scaler))))
    if scaler != None:
        data = scaler.fit_transform(data)

    #classifier = tree.DecisionTreeClassifier()
    #classifier.fit(data, result)
    #return scaler, classifier

    parameters = {
            'criterion':('gini', 'entropy'),
            'splitter':('best','random'),
    }
    print(parameters)
    search = GridSearchCV(tree.DecisionTreeClassifier(), parameters, scoring=scoring, n_jobs=1)
    search.fit(data, result)
    print(("best params: {}".format(search.best_params_)))
    print(("best score: {}".format(search.best_score_)))
    print()
    return scaler, search.best_estimator_.fit(data,result)


def train_svm(data, result, scoring=None):
    print(("train SVC {}".format(len(data))))
    data = np.array(data)
    result = np.array(result)

    #-------------------------------------------------------------
    # Basic score without any data treatment
    #-------------------------------------------------------------

    #classifier = svm.SVC(kernel='rbf')
    #classifier.fit(data, result)
    #print("initial score rbf: {}, custom={}".format(classifier.score(data, result), scoring(classifier, data, result))

    #classifier = svm.SVC(kernel="linear")
    #classifier.fit(data, result)
    #print("initial score linear: {}".format(classifier.score(data, result)))

    #scaler = preprocessing.StandardScaler()
    scaler = preprocessing.MinMaxScaler()
    #scaler = preprocessing.RobustScaler()

    print(("Scale: {}".format(type(scaler))))
    if scaler != None:
        data = scaler.fit_transform(data)

    #classifier = svm.SVC()
    #classifier.fit(data, result)
    #print("initial score: {}, custom={}".format(classifier.score(data, result), scoring(classifier, data, result)))

    parameters = {
        #'kernel':('linear', 'rbf'),
        'kernel':('rbf',),
        # Attention: ca peux marcher mieux si on laisse sans preciser de valeur
        # pour gamma qui prendra la valeur 'auto'
        'gamma': [10**x for x in range(-4,2)],
        #'C': [1]
        #'C': [10**x for x in xrange(-5,5)]
        'C': [10**x for x in range(0,5)]
    }
    print(parameters)
    search = GridSearchCV(svm.SVC(), parameters, scoring=scoring, n_jobs=1)
    search.fit(data, result)
    print(("best params: {}".format(search.best_params_)))
    print(("best score: {}".format(search.best_score_)))
    print()


    C   = search.best_params_['C']
    gamma = search.best_params_['gamma']
    parameters = {
        #'kernel':('linear', 'rbf'),
        'kernel':('rbf',),
        'gamma': [gamma/10.0 + gamma/10.0*i for i in range(1,10)]
             + [gamma + gamma*i for i in range(2,9)],
        'C': [C/10.0 + C/10.0*i for i in range(1,10)]
             + [C + C*i for i in range(1,9)]
    }
    print(parameters)
    search = GridSearchCV(svm.SVC(), parameters, scoring=scoring, n_jobs=1)
    search.fit(data, result)
    print(("best params: {}".format(search.best_params_)))
    print(("best score: {}".format(search.best_score_)))
    print()

    return scaler, search.best_estimator_.fit(data,result)


def train_sgd(data, result, scoring=None):
    print(("train SGDClassifier {}".format(len(data))))
    #scaler = None
    #scaler = preprocessing.MinMaxScaler()
    print(("Scale: {}".format(type(scaler))))
    if scaler != None:
        data = scaler.fit_transform(data)

    #classifier = SGDClassifier(loss="hinge", penalty="l2")
    #classifier.fit(data, result)
    #return scaler, classifier

    parameters = {
        'loss': ('hinge', 'log', 'modified_huber', 'squared_hinge', 'perceptron',
                 'squared_loss', 'huber', 'epsilon_insensitive',
                 'squared_epsilon_insensitive'),
        'penalty': ('none', 'l2', 'l1', 'elasticnet')
    }
    print(parameters)
    search = GridSearchCV(SGDClassifier(), parameters, scoring=scoring, n_jobs=1)
    search.fit(data, result)
    print(("best params: {}".format(search.best_params_)))
    print(("best score: {}".format(search.best_score_)))
    print()
    return scaler, search.best_estimator_.fit(data,result)


def weighted_scoring(y_weights):
    """Return a scoring function that give more weight to some classes"""
    def scoring(estimator, X, y):
        total = 0.0
        ok = 0.0
        for i in range(len(X)):
            weight = y_weights[y[i]]
            total = total + weight
            if estimator.predict(X[i]) == y[i]:
                ok = ok + weight
        return ok / total
    return scoring


def get_segmented_buildings_data(osm_data):
    buildings = []
    for way in itervalues(osm_data.ways):
        if way.isBuilding:
            way.isSegmented = way.tags.get("segmented") not in (None, "?", "no")
            buildings.append(way)
    for rel in itervalues(osm_data.relations):
        if rel.isBuilding:
            rel.isSegmented = rel.tags.get("segmented") not in (None, "?", "no")
            for item, role in osm_data.iter_relation_members(rel):
                if role in ("inner", "outer"):
                    item.hasWall = rel.hasWall
                    item.isSegmented = rel.isSegmented
                    if "segmented" in rel.tags:
                        item.tags["segmented"] = rel.tags["segmented"]
                    buildings.append(item)
    data = []
    result = []
    for building in buildings:
        nodes = [osm_data.nodes[i] for i in building.nodes]
        ways_id = reduce(operator.or_, [node.ways for node in nodes])
        ways = [osm_data.ways[i] for i in ways_id if i != building.id()]
        for way in ways:
            if way.isBuilding and way.id() > building.id():
                vector = get_segmented_analysis_vector_from_osm(osm_data, building, way)
                if vector != None:
                    if building.isSegmented and way.isSegmented and building.tags["segmented"] == way.tags["segmented"]:
                        data.append(vector)
                        result.append(1)
                        # Consider also the switched comparison vector:
                        switched_vector = get_segmented_analysis_vector_from_osm(osm_data, way, building)
                        if switched_vector != None:
                            data.append(switched_vector)
                            result.append(1)
                    elif (building.hasWall == way.hasWall) and ((building.tags.get("segmented") != "?") or (way.tags.get("segmented") != "?")):
                        data.append(vector)
                        result.append(0)
    return data, result



#def get_segmented_analysis_vector_from_polygons(p1, p2):
#    assert(len(p1.interiors) == 0)
#    assert(len(p2.interiors) == 0)
#    return get_classifier_vector_from_wkt(p1.wkt, p2.wkt)


#def osm_way_polygon_wkt(osm_data, way):
#   return "POLYGON ((" + ", ".join(
#               map(lambda p: str(p[0]) + " " + str(p[1]),
#                   [osm_data.nodes[i].position for i in way.nodes])
#           ) + "))"

def osm_way_coords_and_nbways(osm_data, way):
    return [(osm_data.nodes[i].position.x, osm_data.nodes[i].position.y, len(osm_data.nodes[i].ways)) for i in way.nodes]


def get_segmented_analysis_vector_from_osm(osm_data, way1, way2):
    vector = get_classifier_vector_from_coords(
            osm_way_coords_and_nbways(osm_data, way1),
            osm_way_coords_and_nbways(osm_data, way2))
    return vector


def get_external1_common_external2_ways(nodes1, nodes2):
    "return the part of way1 not common with way2, the common part, and the part of way2 not common with way1"
    assert(nodes1[-1] == nodes1[0]) # closed way
    assert(nodes2[-1] == nodes2[0]) # closed way
    nodes1 = nodes1[:-1]
    nodes2 = nodes2[:-1]
    previous_i = len(nodes1)-1
    for i in range(len(nodes1)):
        if nodes1[previous_i] not in nodes2 and nodes1[i] in nodes2:
            j = nodes2.index(nodes1[i])
            if (nodes2[(j + 1) % len(nodes2)] == nodes1[previous_i]) or \
               (nodes2[(j - 1 + len(nodes2)) % len(nodes2)] == nodes1[(i+1) % len(nodes1)]):
                # way2 is in reverse order
                nodes2.reverse()
                j = nodes2.index(nodes1[i])
            nodes1 = nodes1[i:] + nodes1[:i]
            nodes2 = nodes2[j:] + nodes2[:j]
            break
        previous_i = i
    i = 0
    while i<min(len(nodes1),len(nodes2)) and nodes1[i] == nodes2[i]:
        i = i + 1
    if i==0:
       return nodes1+nodes1[0:1], [], nodes2 + nodes2[0:1]
    else:
       return nodes1[i-1:]+nodes1[0:1], nodes1[:i], nodes2[i-1:] + nodes2[0:1]




#def get_segmented_analysis_vector(way1, way2):
#    result = None
#    if way1[-1] == way1[0] and way2[-1] == way2[0]:
#        external1, common, external2 = get_external1_common_external2_ways(way1, way2)
#        if len(common)>1:
#            assert(external1[-1] == common[0])
#            assert(external2[-1] == common[0])
#            assert(common[-1] == external1[0])
#            assert(common[-1] == external2[0])
#
#            #        a-----------b-------------c
#            #        |            \            |
#            #        |             d           |
#            #  way1 ...            ...        ... way2
#            #        |               e         |
#            #        |                \        |
#            #        f-----------------g-------h
#            a = external1[-2]
#            b = common[0]
#            c = external2[-2]
#            d = common[1]
#            e = common[-2]
#            f = external1[1]
#            g = common[-1]
#            h = external2[1]
#
#            data = [ angle_abc(a,b,c),
#                     angle_abc(f,g,h),
#                     angle_abc(a,b,d),
#                     angle_abc(e,g,f),
#                     angle_abc(c,b,d),
#                     angle_abc(e,g,h)]
#
#            data = [angle * 180 / math.pi for angle in data]
#            data.extend([diff_to_90(angle) for angle in data])
#
#            # Compare common length ratio
#            common_length = LineString(common).length
#            external1_length = LineString(external1).length
#            external2_length = LineString(external2).length
#            ratio1 = common_length / external1_length
#            ratio2 = common_length / external2_length
#            data.extend([ratio1 + ratio2 / 2, min(ratio1, ratio2), max(ratio1, ratio2)])
#
#            # Extended common part as they are with the cut on each side:
#            common1_extd = [a] + common + [f]
#            common2_extd = [c] + common + [h]
#            # Consider extended ways, as they would be without the cut:
#            external1_extd = [h] + external1 + [c]
#            external2_extd = [f] + external2 + [a]
#
#            external1_extd_angles, external2_extd_angles, common1_extd_angles, common2_extd_angles = \
#                [ numpy.array([angle_abc(nodes[i-1], nodes[i], nodes[i+1]) * 180 / math.pi for i in xrange(1, len(nodes)-1)])
#                  for nodes in external1_extd, external2_extd, common1_extd, common2_extd]
#
#            data.extend(
#                [external1_extd_angles.mean(), external1_extd_angles.std(), external1_extd_angles.min(), external1_extd_angles.max(),
#                 external2_extd_angles.mean(), external2_extd_angles.std(), external2_extd_angles.min(), external2_extd_angles.max(),
#                 common1_extd_angles.mean() - external1_extd_angles.mean(),
#                 common1_extd_angles.std(),
#                 common1_extd_angles.min() - external1_extd_angles.min(),
#                 common1_extd_angles.max() - external1_extd_angles.max(),
#                 common2_extd_angles.mean() - external2_extd_angles.mean(),
#                 common2_extd_angles.std(),
#                 common2_extd_angles.min() - external2_extd_angles.min(),
#                 common2_extd_angles.max() - external2_extd_angles.max()])
#
#            external1_extd_angles, external2_extd_angles, common1_extd_angles, common2_extd_angles = \
#                [numpy.array([diff_to_90(angle) for angle in angles]) for angles in
#                    external1_extd_angles, external2_extd_angles, common1_extd_angles, common2_extd_angles ]
#
#            data.extend(
#                [external1_extd_angles.mean(), external1_extd_angles.std(), external1_extd_angles.min(), external1_extd_angles.max(),
#                 external2_extd_angles.mean(), external2_extd_angles.std(), external2_extd_angles.min(), external2_extd_angles.max(),
#                 common1_extd_angles.mean() - external1_extd_angles.mean(),
#                 common1_extd_angles.std(),
#                 common1_extd_angles.min() - external1_extd_angles.min(),
#                 common1_extd_angles.max() - external1_extd_angles.max(),
#                 common2_extd_angles.mean() - external2_extd_angles.mean(),
#                 common2_extd_angles.std(),
#                 common2_extd_angles.min() - external2_extd_angles.min(),
#                 common2_extd_angles.max() - external2_extd_angles.max()])
#
#            result = data
#    return result
#
#def length(way):
#    Shapely
#
#def diff_to_90(a):
#    return abs(45-abs(45-(a%90)))
#
#
#def nodes_angle(a,b,c):
#    return angle_abc(a.position, b.position, c.position)
#
#def angle_abc(a,b,c):
#    v1 = numpy.array([a[0]-b[0], a[1]-b[1]])
#    v2 = numpy.array([c[0]-b[0], c[1]-b[1]])
#    d = numpy.linalg.norm(v1) * numpy.linalg.norm(v2)
#    if d == 0:
#        return 0
#    else:
#        return numpy.arccos(numpy.clip(numpy.dot(v1, v2) / d, -1.0, 1.0))
#
#
#def main2(argv):
#    """display buildings of an osm file"""
#    osm = OsmParser().parse(argv[1])
#    inputTransform, outputTransform = get_centered_metric_equirectangular_transformation_from_osm(osm)
#    compute_transformed_position_and_annotate(osm, inputTransform)
#    compute_buildings_polygons_and_rtree(osm, TOLERANCE)
#
#    for way in itervalues(osm.ways):
#        if way.isBuilding:
#            img = draw_buildings_around(osm, way)
#            cv2.imwrite("x-%d.png" % way.id(), img)
#            cv2.imshow('image',img)
#            key = cv2.waitKey(0)
#            if key in (1048689, 1048603):
#                break
#    cv2.destroyAllWindows()
#
#IMG_SIZE = 256
#
#def affine_transform_matrix(angle, scale, tx, ty):
#    """Return a matirx to be used with shapely.affinity.affine_transform"""
#    cos = math.cos(angle)
#    sin = math.sin(angle)
#    return [cos*scale, -sin*scale, sin*scale,  cos*scale, tx, ty]
#
#def angle(p1,p2):
#    return numpy.angle(p2.x-p1.x + 1j*(p2.y-p1.y))
#
#
#def longest_segment_index(coords):
#    max_length = 0
#    max_length_index = 0
#    for i in xrange(len(coords)-1):
#        length = LineString([coords[i], coords[i+1]]).length
#        if length > max_length:
#            max_length = length
#            max_length_index = i
#    return max_length_index
#
#def get_rotation_angle_to_put_vertical_the_longest_segment(polygon):
#    coords = polygon.exterior.coords
#    i = longest_segment_index(coords)
#    p0, p1 = Point(coords[i]), Point(coords[i+1])
#    a = angle(Point((0,0)),Point((0,1))) - angle(p0, p1)
#    rotated_centroid = shapely.affinity.rotate(polygon.centroid, a, origin=p0, use_radians=True)
#    if rotated_centroid.x < p0.x :
#        # Ensure the polygon is mainly on the right of the vertical segment
#        a = a + math.pi
#    return a
#
#
#def get_scale_tx_ty_for_bbox_transform(bbox1, bbox2):
#    minx1,miny1,maxx1,maxy1 = bbox1
#    minx2,miny2,maxx2,maxy2 = bbox2
#    scalex = (maxx2-minx2) / (maxx1-minx1)
#    scaley = (maxy2-miny2) / (maxy1-miny1)
#    scale = min(scalex,scaley)
#    return scale, minx2-minx1*scale, miny2-miny1*scale
#
#
#def search_bbox_for_drawing(polygon):
#    xmin,ymin,xmax,ymax = polygon.bounds
#    size = max(xmax-xmin, ymax-ymin)
#    return xmin-size, ymin-size, xmax+size, ymax+size
#
#def draw_polygon(img, polygon, hasWall):
#    pts = numpy.array(polygon.exterior.coords, numpy.int32)
#    pts = pts.reshape((-1,1,2))
#    cv2.fillPoly(img,[pts],160 if hasWall else 120)
#    for linearring in polygon.interiors:
#        ipts = numpy.array(linearring.coords, numpy.int32)
#        ipts = pts.reshape((-1,1,2))
#        cv2.fillPoly(img,[ipts],0)
#    for linearring in polygon.interiors:
#        ipts = numpy.array(linearring.coords, numpy.int32)
#        ipts = pts.reshape((-1,1,2))
#        cv2.polylines(img,[ipts],True,255, 1, cv2.CV_AA)
#    cv2.polylines(img,[pts],True,255, 1, cv2.CV_AA)
#
#def draw_building(img, building, transformation, joined_pos_list, image_mid_polygon, image_polygon):
#    polygon = shapely.affinity.affine_transform(building.polygon, transformation)
#    draw_polygon(img, polygon, building.hasWall)
#    if building.isSegmented:
#        try:
#          if not image_mid_polygon.intersection(polygon).is_empty:
#            bounds = polygon.intersection(image_polygon).bounds
#            joined_pos_list.append((bounds[0], bounds[1], bounds[2]-bounds[0]+1, bounds[3]-bounds[1]+1))
#        except:
#          pass
#
#def draw_buildings_around(osm_data, building):
#    a = get_rotation_angle_to_put_vertical_the_longest_segment(building.polygon)
#    m = affine_transform_matrix(a, 1, 0, 0)
#    bbox1 = shapely.affinity.affine_transform(building.polygon, m).bounds
#    bbox2 = (IMG_SIZE/3, IMG_SIZE/3, IMG_SIZE*2/3, IMG_SIZE*2/3)
#    scale, tx, ty = get_scale_tx_ty_for_bbox_transform(bbox1, bbox2)
#    m = affine_transform_matrix(a, scale, tx, ty)
#    image_polygon = Polygon([(0,0), (IMG_SIZE,0), (IMG_SIZE, IMG_SIZE), (0, IMG_SIZE), (0,0)])
#    image_mid_polygon = Polygon([(IMG_SIZE/6,IMG_SIZE/6), (IMG_SIZE*5/6,IMG_SIZE/6), (IMG_SIZE*5/6, IMG_SIZE*5/6), (IMG_SIZE/6, IMG_SIZE*5/6), (IMG_SIZE/6,IMG_SIZE/6)])
#    joined_pos_list = []
#    img = numpy.zeros((IMG_SIZE,IMG_SIZE), numpy.uint8)
#    draw_building(img, building, m, joined_pos_list, image_mid_polygon, image_polygon)
#    rtree=osm_data.buildings_rtree
#    search_bbox = search_bbox_for_drawing(building.polygon)
#    other_buildings = [osm_data.get(e.object) for e in rtree.intersection(search_bbox, objects=True)]
#    other_buildings = [b for b in other_buildings  if b.isBuilding and (b.id() != building.id())]
#    for b in other_buildings:
#        # Draw first the all the multipolygons
#        if len(b.polygon.interiors) != 0:
#            draw_building(img, b, m, joined_pos_list, image_mid_polygon, image_polygon)
#    for b in other_buildings:
#        if len(b.polygon.interiors) == 0:
#            draw_building(img, b, m, joined_pos_list, image_mid_polygon, image_polygon)
#    return img, joined_pos_list
#
#def save_segmented_images(osm_data, prefix):
#    # The aim was to use opencv image classification but training for
#    # big images need too much processing power
#    rtree=osm_data.buildings_rtree
#    for building in itertools.chain(itervalues(osm_data.ways), itervalues(osm_data.relations)):
#        if building.isBuilding:
#            search_bbox = search_bbox_for_drawing(building.polygon)
#            other_buildings = [osm_data.get(e.object) for e in rtree.intersection(search_bbox, objects=True)]
#            other_buildings = [b for b in other_buildings  if b.isBuilding and (b.id() != building.id())]
#            if building.isSegmented:
#                filename = "positive/%s-%d.png" % (prefix, building.id())
#            else:
#                other_buildings_joined = [b.isSegmented for b in other_buildings]
#                if any(other_buildings_joined):
#                    filename = None
#                else:
#                    filename = "negative/%s-%d.png" % (prefix, building.id())
#            if filename:
#                print(filename)
#                img, joined_pos_list = draw_buildings_around(osm_data, building)
#                cv2.imwrite(filename, img)
#                info = open(filename[:-4] + ".txt", "w")
#                info.write("%d" % len(joined_pos_list))
#                for pos in joined_pos_list:
#                    info.write(" %d %d %d %d" % pos)
#                info.write("\n")
#                info.close()



