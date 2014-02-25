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

Fusionne un fichier OSM avec un autre contenant des nodes "addr:housenumber".

Le programme vas essayer d'inclure le node addr:housenumber dans le way du "building" 
ou de la "barrier" la plus proche.
Il vas aussi chercher le way le plus proche pour positionner le tag "addr:street" du node. 

"""

import sys
import math
import codecs
import os.path
import traceback
import urllib2
import xml.parsers.expat
import xml.sax.saxutils
try:
    import rtree
except:
    traceback.print_exc()
    sys.stdout.write("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
    sys.stdout.write("!!                    ATTENTION !\n");
    sys.stdout.write("!!\n")
    sys.stdout.write("!! SVP installez la bibliothèque rtree pour de bien meilleur performance de fusion.\n")
    sys.stdout.write("!!\n")
    sys.stdout.write("!!        http://pypi.python.org/pypi/Rtree/\n");
    sys.stdout.write("!!\n")
    sys.stdout.write("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")


# Distance max des buildings auxquels les noeuds addr:housenumber vont être intégrés:
BUILDING_MERGE_DISTANCE_IN_METTER = 3.0
# Distance max du highway pour affecter le nom de la rue associée à un noeud addr:housenumber:
HIGHWAY_SAFE_DISTANCE_IN_METTER = 10.0
# Distance max des highways pour considérer qu'il y a ambiguité si il y en a plusieurs de nom différents:
HIGHWAY_AMBIGUITY_DISTANCE_IN_METTER = 15.0
# Distance max pour ne pas fusionner les addr:housenumber déjà présents avec le même numéro:
HOUSENUMBER_MERGE_DISTANCE_IN_METTER = 10.0
EARTH_RAY_IN_METTER = 6371000.0

def usage(error_msg=""):
    print "Fusionne un fichier osm avec un autre contenant des node addr:housenumber."
    if error_msg:
        print "ERREUR:", error_msg
    print "USAGE:", sys.argv[0], \
        " [<input.osm>] <housenumbers.osm> <output.osm>"
    if error_msg:
        sys.exit(-1)
    else:
        sys.exit(0)
        
def degree_to_radian(v):
    return v * math.pi / 180
def radian_to_degree(v):
    return v * 180 / math.pi

class Point(object):
    def __init__(self, x,y):
        self.x = x
        self.y = y

def nearest_point_from_segment_ab_to_point_c(a,b,c):
    # http://www.codeguru.com/forum/printthread.php?t=194400
    r_numerator = (c.x-a.x)*(b.x-a.x) + (c.y-a.y)*(b.y-a.y)
    r_denomenator = (b.x-a.x)*(b.x-a.x) + (b.y-a.y)*(b.y-a.y)
    if r_denomenator == 0:
        return a;
    r = r_numerator / r_denomenator;
    if (r <=0):
        return a
    elif (r>=1):
        return b
    else:
        x = a.x + r*(b.x-a.x)
        y = a.y + r*(b.y-a.y)
        return Point(x,y)
    
def square(a):
    return a*a

def distance_in_metters(a,b):
    # http://fr.wikipedia.org/wiki/Distance_du_grand_cercle
    alon,alat = xy_to_radian_lonlat(a.x,a.y)
    blon,blat = xy_to_radian_lonlat(b.x,b.y)
    R = EARTH_RAY_IN_METTER
    result = 2*R*math.asin(math.sqrt(
        square(math.sin((blat-alat)/2)) 
        + math.cos(alat)*math.cos(blat)*square(math.sin((blon-alon)/2))
    ));
    return result
    
def point_inside_bbox(p,bbox):
    xmin,ymin,xmax,ymax = bbox
    return (p.x >= xmin) and (p.x <= xmax) and (p.y >= ymin) and (p.y <= ymax)

def lonlat_to_xy(lon,lat):
    # Mercator
    return radian_lonlat_to_xy(degree_to_radian(lon), degree_to_radian(lat))

def radian_lonlat_to_xy(lon,lat):
    # Mercator
    x = lon
    y = math.log(math.tan(math.pi/4 + lat/2));
    return x,y

def bbox_around_point_in_metters(point, metters):
    lon,lat = xy_to_radian_lonlat(point.x, point.y);
    rad = math.asin(metters / EARTH_RAY_IN_METTER)
    x1,y1 = radian_lonlat_to_xy(lon+rad, lat+rad)
    x2 = 2*point.x - x1
    y2 = 2*point.y - y1
    return min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)

def xy_to_radian_lonlat(x, y):
    # Mercator
    lon = x;
    lat = math.atan(math.sinh(y))
    return lon,lat

def xy_to_lonlat(x, y):
    # Mercator
    lon = radian_to_degree(x)
    lat = radian_to_degree(math.atan(math.sinh(y)))
    return lon,lat

class Osm(object):
    def __init__(self, attrs):
        self.attrs = attrs;
        self.nodes = {}
        self.ways = {}
        self.relations = {}
        self.min_node_id = 0;
        self.min_way_id = 0;
        self.min_relation_id = 0;
    def add_node(self, node):
        if (node.attrs.has_key("id")):
            id = int(node.attrs["id"])
        else:
            id = -1;
        if (id >= 0):
            assert(not self.nodes.has_key(id))
        else:
            id = self.min_node_id - 1
            self.min_node_id = min(self.min_node_id, id)
            node.attrs["id"] = str(id)
        self.nodes[id] = node
    def add_way(self, way):
        if (way.attrs.has_key("id")):
            id = int(way.attrs["id"])
        else:
            id = -1;
        if (id >= 0):
            assert(not self.ways.has_key(id))
        else:
            id = self.min_way_id - 1
            self.min_way_id = min(self.min_way_id, id)
            way.attrs["id"] = str(id)
        self.ways[id] = way
    def add_relation(self, relation):
        if (relation.attrs.has_key("id")):
            id = int(relation.attrs["id"])
        else:
            id = -1;
        if (id >= 0):
            assert(not self.relations.has_key(id))
        else:
            id = self.min_relation_id - 1
            self.min_relation_id = min(self.min_relation_id, id)
            relation.attrs["id"] = str(id)
        self.relations[id] = relation
    def bbox(self):
        xmin,ymin = lonlat_to_xy(
            float(self.bounds["minlon"]), float(self.bounds["minlat"]))
        xmax,ymax = lonlat_to_xy(
            float(self.bounds["maxlon"]), float(self.bounds["maxlat"]))
        xmin,xmax = min(xmin,xmax), max(xmin,xmax)
        ymin,ymax = min(ymin,ymax), max(ymin,ymax)
        return xmin,ymin,xmax,ymax
    def set_bbox(self,bbox):
        xmin,ymin,xmax,ymax = bbox
        self.bounds["minlon"] = xmin
        self.bounds["minllat"] = ymin
        self.bounds["maxlon"] = xmax
        self.bounds["maxllat"] = ymax

class Node(object):
    def __init__(self, attrs,tags=None):
        self.attrs = attrs
        self.tags = tags or {}
        self.compute_x_y()
    def compute_x_y(self):
        self.x, self.y = lonlat_to_xy(
                float(self.attrs["lon"]), float(self.attrs["lat"]))
    def set_x_y(self, x, y):
        self.x = x
        self.y = y
        self.attrs["lon"], self.attrs["lat"] = map(str, xy_to_lonlat(x,y))
    def id(self):
        return int(self.attrs["id"])

class Way(object):
    def __init__(self, attrs,tags=None):
        self.attrs = attrs
        self.tags = tags or {}
        self.nodes = []
    def add_node(self, node):
        self.nodes.append(node)
    def bbox(self):
        xmin,ymin = self.nodes[0].x, self.nodes[0].y
        xmax,ymax = xmin,ymin
        for node in self.nodes:
            xmin = min(xmin, node.x)
            xmax = max(xmax, node.x)
            ymin = min(ymin, node.y)
            ymax = max(ymax, node.y)
        return xmin,ymin,xmax,ymax
    def id(self):
        return int(self.attrs["id"])
        

class Relation(object):
    def __init__(self, attrs,tags=None):
        self.attrs = attrs
        self.tags = tags or {}
        self.members = []
    def add_member(self, member):
        self.members.append(member)
    def id(self):
        return int(self.attrs["id"])

class OsmParser(object):
    def __init__(self):
        self.parser = xml.parsers.expat.ParserCreate("utf-8")
        assert(self.parser.SetParamEntityParsing(
            xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER))
        self.parser.buffer_text = True
        self.parser.CharacterDataHandler = self.handle_char_data
        self.parser.StartElementHandler = self.handle_start_element
        self.parser.EndElementHandler = self.handle_end_element
    def parse(self, f):
        if type(f) == str:
          self.filename = f
          f = open(f)
        else:
          self.filename = None
        self.osm = None
        self.parser.ParseFile(f)
        return self.osm
    def handle_start_element(self,name, attrs):
        if name == "osm":
            osm = Osm(attrs)
            self.osm = osm
            self.current = None
        elif name == "bounds":
            self.osm.bounds = attrs
        elif name == "node":
            node = Node(attrs);
            self.osm.add_node(node)
            self.current = node
        elif name == "way":
            way = Way(attrs)
            self.osm.add_way(way)
            self.current = way
        elif name == "nd":
            ref = int(attrs["ref"])
            refnode = self.osm.nodes[ref]
            way = self.current
            way.add_node(refnode)
        elif name == "tag":
            self.current.tags[attrs["k"]] = attrs["v"];
        elif name == "relation":
            relation = Relation(attrs)
            self.osm.add_relation(relation)
            self.current = relation
        elif name == "member":
            member = attrs
            relation = self.current
            relation.add_member(member)
        else:
            raise Exception("ERROR: unknown tag <"+name+"> in file " 
                    + filename + "\n")
    def handle_end_element(self,name):
        pass
    def handle_char_data(self,data):
        pass
 
class OsmWriter(object):
    def __init__(self, osm):
        self.osm = osm
    def write_to_file(self, filename):
        self.output = codecs.open(filename, encoding="utf-8", mode="w")
        self.write()
        self.output.close()
    def write(self):
        osm = self.osm
        output = self.output
        output.write("<?xml version='1.0' encoding='UTF-8'?>\n");
        output.write("<osm" + self.attrs_str(osm.attrs) + ">\n");
        output.write("\t<bounds" + self.attrs_str(osm.bounds) + "/>\n");
        for node in osm.nodes.itervalues():
            if len(node.tags):
                output.write("\t<node" + self.attrs_str(node.attrs) + ">\n");
                self.write_tags(node.tags)
                output.write("\t</node>\n");
            else:    
                output.write("\t<node" + self.attrs_str(node.attrs) + "/>\n");
        for way in osm.ways.itervalues():
            output.write("\t<way" + self.attrs_str(way.attrs) + ">\n");
            for node in way.nodes:
                output.write('\t\t<nd ref="' + node.attrs["id"] + '"/>\n');
            self.write_tags(way.tags)
            output.write("\t</way>\n");
        for relation in osm.relations.itervalues():
            output.write("\t<relation" 
                + self.attrs_str(relation.attrs) + ">\n");
            self.write_tags(relation.tags)
            for member in relation.members:
                output.write('\t\t<member' + self.attrs_str(member) + "/>\n");
            output.write("\t</relation>\n");
        output.write("</osm>\n");
    def attrs_str(self, attrs):
        return "".join([' ' + key + '=' + xml.sax.saxutils.quoteattr(value)
            for key,value in attrs.iteritems()])
    def write_tags(self, tags):
        for key,value in tags.iteritems():
            self.output.write('\t\t<tag k="' + key + '" v=' +
                xml.sax.saxutils.quoteattr(value) +'/>\n')



if len(sys.argv) < 3:
    usage("pas assez d'arguments");
if len(sys.argv) > 4:
    usage("trop d'arguments");

if len(sys.argv) == 3:
  input_filename        = None
  housenumbers_filename = sys.argv[1];
  output_filename       = sys.argv[2];
else:
  input_filename        = sys.argv[1];
  housenumbers_filename = sys.argv[2];
  output_filename       = sys.argv[3];

if input_filename and (not os.path.isfile(input_filename)):
    usage("fichier d'entrée non trouvé:" + input_filename);
if not os.path.isfile(housenumbers_filename):
    usage("fichier housenumbers non trouvé:" + housenumbers_filename);
#if os.path.exists(output_filename):
#    usage("le fichier de sortie existe déjà:" + output_filename);
#if input_filename and (os.path.splitext(input_filename)[1] != ".osm"):
#    usage("le fichier d'entrée n'est pas un fichier .osm:" + input_filename);
#if os.path.splitext(housenumbers_filename)[1] != ".osm":
#    usage("le fichier housenumbers n'est pas un fichier .osm:" + housenumbers_filename);
#if os.path.splitext(output_filename)[1] != ".osm":
#    usage("le fichier de sortie n'est pas un fichier .osm:" + output_filename);


print "parse le fichier d'housenumbers " + housenumbers_filename + " ..."
housenumbers_osm = OsmParser().parse(housenumbers_filename)

if len(housenumbers_osm.ways) > 0 or len(housenumbers_osm.relations) > 0:
    usage("le fichier housenumbers ne contient pas que des nodes addr:housenumber")
for node in housenumbers_osm.nodes.itervalues():
    if not node.tags.has_key("addr:housenumber"):
        usage("le fichier housenumbers ne contient pas que des nodes addr:housenumber")
if len(housenumbers_osm.nodes) == 0:
    usage("le fichier housenumbers est vide.")

if input_filename:
    sys.stdout.write((u"parse le fichier d'entrée " + input_filename + " ...\n").encode("utf-8"))
    input_osm = OsmParser().parse(input_filename)
else:
    # Get input data from OSM server
    # Compute bbox of data to get:
    marge_deg = radian_to_degree(
        math.asin(
          max(BUILDING_MERGE_DISTANCE_IN_METTER , HIGHWAY_SAFE_DISTANCE_IN_METTER, 
             HIGHWAY_AMBIGUITY_DISTANCE_IN_METTER, HOUSENUMBER_MERGE_DISTANCE_IN_METTER)
          * 2 / EARTH_RAY_IN_METTER))
    minlon = min(float(n.attrs["lon"]) for n in housenumbers_osm.nodes.values()) - marge_deg
    minlat = min(float(n.attrs["lat"]) for n in housenumbers_osm.nodes.values()) - marge_deg
    maxlon = max(float(n.attrs["lon"]) for n in housenumbers_osm.nodes.values()) + marge_deg
    maxlat = max(float(n.attrs["lat"]) for n in housenumbers_osm.nodes.values()) + marge_deg
    url="http://api.openstreetmap.org/api/0.6/map?bbox=%f,%f,%f,%f" % (minlon, minlat, maxlon, maxlat)
    print url
    sys.stdout.flush()
    sys.stdout.write((u"parse les données du server OSM ...\n").encode("utf-8"))
    input_osm = OsmParser().parse(urllib2.urlopen(url))

output_osm = input_osm

sys.stdout.write("fusionne...\n")
sys.stdout.flush()
buildings = []
highways = []
housenumbers = []
for way in input_osm.ways.itervalues():
    if way.tags.has_key("building") or way.tags.has_key("barrier"):
        buildings.append(way)
    if way.tags.has_key("highway"):
        highways.append(way)
for node in input_osm.nodes.itervalues():
  if node.tags.has_key("addr:housenumber"):
    housenumbers.append(node)

if locals().has_key("rtree"):
    buildings_rtree = rtree.Rtree()
    for way in buildings:
        id = way.id()
        buildings_rtree.add(id, way.bbox(), obj=id)
    highways_rtree = rtree.Rtree()
    for way in highways:
        id = way.id()
        highways_rtree.add(id, way.bbox(), obj=id)
    housenumbers_rtree = rtree.Rtree()
    for node in housenumbers:
        id = node.id()
        housenumbers_rtree.add(id, (node.x, node.y), obj=id)


else:
    buildings_rtree = None
    highways_rtree = None
    housenumbers_rtree = None

def buildings_list_near_node(node):
    if buildings_rtree != None:
        intersection_bbox = bbox_around_point_in_metters(
            node, BUILDING_MERGE_DISTANCE_IN_METTER)
        # we use objects=True to store the id because rtree 
        # convert negative id to positive one (it use unsigned integer)
        return [input_osm.ways[way_id_object.object] for way_id_object
            in buildings_rtree.intersection(intersection_bbox, objects=True)]
    else:
        # no rtree library, 
        # return all buildings => O(N*N) computation, very slow !!!
        return buildings

def highways_list_near_node(node):
    if highways_rtree != None:
        intersection_bbox = bbox_around_point_in_metters(node,
            max(HIGHWAY_SAFE_DISTANCE_IN_METTER, 
                HIGHWAY_AMBIGUITY_DISTANCE_IN_METTER))
        # we use objects=True to store the id because rtree 
        # convert negative id to positive one (it use unsigned integer)
        return [input_osm.ways[way_id_object.object] for way_id_object
            in highways_rtree.intersection(intersection_bbox, objects=True)]
    else:
        # no rtree library, 
        # return all highways => O(N*N) computation, very slow !!!
        return highways

def housenumbers_list_near_node(node):
    if housenumbers_rtree != None:
        intersection_bbox = bbox_around_point_in_metters(
            node, HOUSENUMBER_MERGE_DISTANCE_IN_METTER)
        # we use objects=True to store the id because rtree 
        # convert negative id to positive one (it use unsigned integer)
        return [input_osm.nodes[node_id_object.object] for node_id_object
            in housenumbers_rtree.intersection(intersection_bbox, objects=True)]
    else:
      return housenumber

def housenumber_already_exist(node):
  v = node.tags["addr:housenumber"]
  for n in housenumbers_list_near_node(node):
      if n.tags["addr:housenumber"] == v:
        if distance_in_metters(n,node) <= HOUSENUMBER_MERGE_DISTANCE_IN_METTER:
          return True
  return False


def search_nearest_way(node, ways, max_distance):
    """ Search the way from ways that is the nearest to the given node.
        return the tuple (
                way      : the nearest way from the input list
                distance : the distance from the input node to the nearest way
                segment  : the node index of the nearest segment of the way
                point    : the nearest point on the segment
                ways     : all the ways from the input list that are nearer than max_distance
        )
    """
    best_distance = float("inf")
    best_way = None
    best_segment_index = None
    best_point = None
    near_ways = {}
    for way in ways:
            for i in xrange(0, len(way.nodes)-1):
                a = way.nodes[i]
                b = way.nodes[i+1]
                p = nearest_point_from_segment_ab_to_point_c(a,b,node)
                d = distance_in_metters(node, p);
                if d <= max_distance:
                  near_ways[way] = True
                  if d <= best_distance:
                      best_distance = d
                      best_way = way
                      best_segment_index = i
                      best_point = p
    return best_way, best_distance, best_segment_index, best_point, near_ways.keys()


input_osm_bbox = input_osm.bbox();
for node in housenumbers_osm.nodes.itervalues():
    if point_inside_bbox(node, input_osm_bbox) \
            and node.tags.has_key("addr:housenumber") \
            and not housenumber_already_exist(node):  

        #print "node ", node.x, node.y

        # recherche la rue la plus proche:
        if (not node.tags.has_key("addr:street")) or \
                (not node.tags["addr:street"]):
            nearest_way, distance, segment_index, point , ambiguity_ways = \
                search_nearest_way(node, highways_list_near_node(node), HIGHWAY_AMBIGUITY_DISTANCE_IN_METTER)
            #print "best highway distance ", distance

            # Compte le nombre de nom de rue différents dans la zone, si il y en a plus d'un,
            # alors considère qu'il y a ambiguité, et que l'on ne peut pas être sur du nom de la rue
            ambiguity_names = {}
            for way in ambiguity_ways:
              if way.tags.has_key("name"):
                ambiguity_names[way.tags["name"]] = True
              
            if (len(ambiguity_names) == 1) and (distance <= HIGHWAY_SAFE_DISTANCE_IN_METTER):
                if nearest_way.tags.has_key("name"):
                    #print "found street " + way.tags["name"]
                    node.tags["addr:street"] = nearest_way.tags["name"]
                    node.attrs["action"] = "modify" # for JOSM

        # Recherche de l'imeuble le plus près:
        way, distance, segment_index, point, _ = \
            search_nearest_way(node, buildings_list_near_node(node), BUILDING_MERGE_DISTANCE_IN_METTER)
        #print "best building distance ", distance
        new_node = Node(attrs=node.attrs.copy(), tags=node.tags)
        output_osm.add_node(new_node)
        # supprime des tag de debuggage interne:
        #for tag in ("debug","svg","width", "diag","height","debug:svg","debug:info"):
        #    if new_node.tags.has_key(tag):
        #        del(new_node.tags[tag])
        new_node.attrs["action"] = "modify" # for JOSM
        if way:
            a = way.nodes[segment_index]
            b = way.nodes[segment_index+1]
            if (point != a) and (point != b):
                # Ajoute le noeud dans le chemin de l'imeuble:
                new_node.set_x_y(point.x, point.y)
                way.nodes.insert(segment_index+1, new_node)
                way.attrs["action"] = "modify" # for JOSM
                if way.tags.has_key("addr:housenumber") and way.tags["addr:housenumber"] == node.tags["addr:housenumber"]:
                  # L'imeuble était déjà tagué avec ce même numéro de rue.
                  # On déplace alors tout les tag addr:* depuis l'imeuble vers 
                  # le noeud adresse que l'on rajoute à l'imeuble.
                  for k in way.tags.keys():
                    if k.startswith("addr:"):
                      new_node.tags[k] = way.tags[k]
                      del(way.tags[k])

sys.stdout.write("écrit le fichier de sortie...\n")
writer = OsmWriter(output_osm)
writer.write_to_file(output_filename)

