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
Prends en entrée des fichier osm contenant des building avec
un tag "segmented" contenant des valeurs égales pour les buildings à fusionner,
ou rien ou "segmented"="no" pour ceux à ne pas fusioner,
et "segmented"="?" pour ceux pour lequel c'est ambigue.

De tels fichiers d'entrée peuvent être générés par le programme 
segmented_building_find_joined.py

La sortie de ce programme est la gérération d'un fichier 
    classifier.pickle 
dump d'une instance de classifier pour prédire deux bâtiments fractionnés
avec la fonction 
    fr_cadastre_segmented.get_classifier_vector(wkt1, wkt2)

Il y a aussi la génération de fichiers:
    classifier.mean 
    classifier.scale
Contenant une liste de float à passer en parramètre à la fonction
    fr_cadastre_segmented.set_vector_mean_and_scale(mean_list, scale_list)
"""


import re
import sys
import copy
import math
import numpy as np
import pickle
import os.path
import zipfile
import operator
import itertools
from sklearn import svm, grid_search
from sklearn import preprocessing


from osm                            import Osm,Node,Way,Relation,OsmParser,OsmWriter
from simplify_qadastre_houses       import get_centered_metric_equirectangular_transformation
from segmented_building_find_joined import compute_transformed_position_and_annotate
from fr_cadastre_segmented          import get_classifier_vector


def main(argv):
    osm_args = [f for f in argv[1:] if os.path.splitext(f)[1] in (".zip", ".osm")]
    other_args = [f for f in argv[1:] if os.path.splitext(f)[1] not in (".zip", ".osm")]
    if len(other_args) != 0:
        return print_usage("invalid argument: " + other_args[0])
    if len(osm_args) == 0:
        return print_usage("not enough file.osm args")

    all_data = []
    all_result = []

    for name, stream in open_zip_and_files_with_extension(osm_args, ".osm"):
        print "load " + name
        osm = OsmParser().parse_stream(stream)
        inputTransform, outputTransform = get_centered_metric_equirectangular_transformation(osm)
        compute_transformed_position_and_annotate(osm, inputTransform)

        data, result = get_segmented_buildings_data(osm)

        print " ->", len(result), "cas", result.count(1), " positif"
        all_data.extend(data)
        all_result.extend(result)

    scaler, classifier = train(all_data, all_result)
    with open("classifier.pickle", "w") as f:
        pickle.dump(classifier, f)
    with open("scaler.pickle", "w") as f:
        pickle.dump(scaler, f)

    #for positive_weight in 1,2,5:
    #    print "-------------------------------------------------------------"
    #    print "Train with scoring for positive segemented building weighted %d over non segmented ones" % positive_weight
    #    scaler, classifier = train(all_data, all_result, weighted_scoring([1,positive_weight]))
    #    with open("classifier_%d.txt" % positive_weight, "w") as f:
    #        f.write(str(classifier))
    #        f.write("\n")
    #    with open("classifier_%d.pickle" % positive_weight, "w") as f:
    #        pickle.dump(classifier, f)
    #    with open("scaler_%d.pickle" % positive_weight, "w") as f:
    #        pickle.dump(scaler, f)

    return 1


def train(data, result, scoring=None):
    data = np.array(data)
    result = np.array(result)

    #-------------------------------------------------------------
    # Basic score without any data treatment
    #-------------------------------------------------------------

    #classifier = svm.SVC(kernel='rbf')
    #classifier.fit(data, result)
    #print "initial score rbf: ", classifier.score(data, result), "custom=", scoring(classifier, data, result)

    #classifier = svm.SVC(kernel="linear")
    #classifier.fit(data, result)
    #print "initial score linear: ", classifier.score(data, result)

    #scaler = preprocessing.StandardScaler()
    scaler = preprocessing.MinMaxScaler()
    #scaler = preprocessing.RobustScaler()

    print "Scale: ", type(scaler)
    if scaler != None:
        data = scaler.fit_transform(data)

    #classifier = svm.SVC()
    #classifier.fit(data, result)
    #print "initial score: ", classifier.score(data, result), "custom=", scoring(classifier, data, result)

    parameters = {
        #'kernel':('linear', 'rbf'),
        'kernel':('rbf',),
        # Attention: ca peux marcher mieux si on laisse sans preciser de valeur
        # pour gamma qui prendra la valeur 'auto'
        'gamma': [10**x for x in xrange(-4,2)],
        #'C': [1]
        #'C': [10**x for x in xrange(-5,5)]
        'C': [10**x for x in xrange(0,5)]
    }
    print parameters
    search = grid_search.GridSearchCV(svm.SVC(), parameters, scoring=scoring, n_jobs=1)
    search.fit(data, result)
    print "best params:", search.best_params_
    print "best score:", search.best_score_
    print


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
    print parameters
    search = grid_search.GridSearchCV(svm.SVC(), parameters, scoring=scoring, n_jobs=1)
    search.fit(data, result)
    print "best params:", search.best_params_
    print "best score:", search.best_score_
    print

    return scaler, search.best_estimator_.fit(data,result)


def weighted_scoring(y_weights):
    """Return a scoring function that give more weight to some classes"""
    def scoring(estimator, X, y):
        total = 0.0
        ok = 0.0
        for i in xrange(len(X)):
            weight = y_weights[y[i]]
            total = total + weight
            if estimator.predict(X[i]) == y[i]:
                ok = ok + weight
        return ok / total
    return scoring


def print_usage(error=""):
    if error: print "ERROR:", error
    print "USAGE: %s buildins-with-segmented-tag.osm" % (sys.argv[0],)
    if error:
        return -1
    else:
        return 0

def open_zip_and_files_with_extension(file_list, extension):
    for name in file_list:
        if name.endswith(".zip"):
            inputzip = zipfile.ZipFile(name, "r")
            for name in inputzip.namelist():
                if name.endswith(extension):
                    f = inputzip.open(name)
                    yield name, f
                    f.close()
            inputzip.close()
        elif name.endswith(extension):
            f = open(name)
            yield name, f
            f.close()


def get_segmented_buildings_data(osm_data):
    buildings = []
    for way in osm_data.ways.itervalues():
        if way.isBuilding:
            way.isSegmented = way.tags.get("segmented") not in (None, "?", "no")
            buildings.append(way)
    for rel in osm_data.relations.itervalues():
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



def get_segmented_analysis_vector_from_polygons(p1, p2):
    assert(len(p1.interiors) == 0)
    assert(len(p2.interiors) == 0)
    return get_classifier_vector(p1.wkt, p2.wkt)

def osm_way_polygon_wkt(osm_data, way):
    return "POLYGON ((" + ", ".join(
                map(lambda p: str(p[0]) + " " + str(p[1]), 
                    [osm_data.nodes[i].position for i in way.nodes])
            ) + "))"


def get_segmented_analysis_vector_from_osm(osm_data, way1, way2):
    way1_wkt = osm_way_polygon_wkt(osm_data, way1)
    way2_wkt = osm_way_polygon_wkt(osm_data, way2)
    vector = get_classifier_vector(way1_wkt, way2_wkt)
    return vector


def get_external1_common_external2_ways(nodes1, nodes2):
    "return the part of way1 not common with way2, the common part, and the part of way2 not common with way1"
    assert(nodes1[-1] == nodes1[0]) # closed way
    assert(nodes2[-1] == nodes2[0]) # closed way
    nodes1 = nodes1[:-1]
    nodes2 = nodes2[:-1]
    previous_i = len(nodes1)-1
    for i in xrange(len(nodes1)):
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
#    inputTransform, outputTransform = get_centered_metric_equirectangular_transformation(osm)
#    compute_transformed_position_and_annotate(osm, inputTransform)
#    compute_buildings_polygons_and_rtree(osm, TOLERANCE)
#
#    for way in osm.ways.itervalues():
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
#    for building in itertools.chain(osm_data.ways.itervalues(), osm_data.relations.itervalues()):
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
#                print filename
#                img, joined_pos_list = draw_buildings_around(osm_data, building)
#                cv2.imwrite(filename, img)
#                info = open(filename[:-4] + ".txt", "w")
#                info.write("%d" % len(joined_pos_list))
#                for pos in joined_pos_list:
#                    info.write(" %d %d %d %d" % pos)
#                info.write("\n")
#                info.close()

    
if __name__ == '__main__':
    sys.exit(main(sys.argv))

