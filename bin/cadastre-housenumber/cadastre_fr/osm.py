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

OSM file Parser/Writer

"""

import sys
import math
import os.path
import xml.sax.saxutils
import xml.parsers.expat
import itertools


class Osm(object):
    min_id = 0
    def __init__(self, attrs):
        self.attrs = {}
        self.attrs.update(attrs);
        self.nodes = {}
        self.ways = {}
        self.relations = {}
        self.bounds = []
        if not self.attrs.has_key('version'):
          self.attrs['version'] = '0.6'
        if not self.attrs.has_key('generator'):
          self.attrs['generator'] = os.path.basename(sys.argv[0])
    def add_node(self, node):
        id = node.id()
        assert(not self.nodes.has_key(id))
        self.nodes[id] = node
    def create_node(self, attrs,tags=None):
        node = Node(attrs, tags)
        self.add_node(node)
        return node
    def add_way(self, way):
        id = way.id()
        assert(not self.ways.has_key(id))
        self.ways[id] = way
    def create_way(self, attrs,tags=None):
        way = Way(attrs, tags)
        self.add_way(way)
        return way
    def add_relation(self, relation):
        id = relation.id()
        assert(not self.relations.has_key(id))
        self.relations[id] = relation
    def create_relation(self, attrs,tags=None):
        relation = Relation(attrs, tags)
        self.add_relation(relation)
        return relation
    def add_bounds(self, bounds_attrs):
        """bounds_attrs: a hashtabe with keys 'minlon', 'minlat', 'maxlon' and 'maxlat'.""" 
        self.bounds.append(bounds_attrs)
    def bbox(self):
        if len(self.bounds):
            minlon = min([float(b["minlon"]) for b in self.bounds])
            minlat = min([float(b["minlat"]) for b in self.bounds])
            maxlon = max([float(b["maxlon"]) for b in self.bounds])
            maxlat = max([float(b["maxlat"]) for b in self.bounds])
        else:
            minlon = min([n.lon() for n in self.nodes.itervalues()])
            minlat = min([n.lat() for n in self.nodes.itervalues()])
            maxlon = max([n.lon() for n in self.nodes.itervalues()])
            maxlat = max([n.lat() for n in self.nodes.itervalues()])
        return minlon,minlat,maxlon,maxlat
    def set_bbox(self,bbox):
        minlon,minlat,maxlon,maxlat = bbox
        self.bounds = []
        self.bounds.append({
          "minlon": str(minlon),
          "minlat": str(minlat),
          "maxlon": str(maxlon),
          "maxlat": str(maxlat)})
    def update_bbox(self):
        self.bounds = []
        self.set_bbox(self.bbox())
    def iteritems(self):
        return itertools.chain.from_iterable(
                [self.nodes.itervalues(), 
                 self.ways.itervalues(), 
                 self.relations.itervalues()])
    def get(self, item_type_or_textid, item_id=None):
        if item_type_or_textid in ("n", "node"):
            return self.nodes.get(item_id)
        elif item_type_or_textid  in ("w",  "way"):
            return self.ways.get(item_id)
        elif item_type_or_textid  in ("r", "relation"):
            return self.relations.get(item_id)
        else: # consider we have a textid
            assert(item_id == None)
            item_type = item_type_or_textid[0]
            item_id = int(item_type_or_textid[1:])
            return self.get(item_type, item_id)
    def iter_relation_members(self, relation):
        for mtype, mref, mrole in relation.itermembers():
            yield self.get(mtype, int(mref)), mrole
    def filter(self, items):
        """ Return a new Osm() file, in which only the listed items 
            and the dependent ones) are present
        """
        result = Osm({})
        def add_item(i):
            if i.type() == "node":
              add_node(i)
            elif i.type() == "way":
              add_way(i)
            elif i.type() == "relation":
              add_relation(i)
        def add_node(n):
            result.nodes[n.id()] = n
        def add_way(w):
            result.ways[w.id()] = w
            for node_id in w.nodes: add_node(self.nodes[node_id])
        def add_relation(r):
            result.relations[r.id()] = r
            for item, role in self.iter_relation_members(r):
                add_item(i)
        for i in items:
            add_item(i)
        return result



class Item(object):
    def __init__(self, attrs,tags=None):
        self.attrs = attrs
        self.tags = tags or {}
        if (attrs.has_key("id")):
            id = int(attrs["id"])
        else:
            id = Osm.min_id - 1
            attrs["id"] = str(id)
        Osm.min_id = min(Osm.min_id, id)
    def id(self):
        return int(self.attrs["id"])
    def textid(self):
        return self.type()[0] + str(self.id())

class Node(Item):
    def __init__(self, attrs,tags=None):
        Item.__init__(self, attrs, tags)
    def type(self):
        return "node"
    def lon(self):
      return float(self.attrs["lon"])
    def lat(self):
      return float(self.attrs["lat"])
    def distance(self, node):
        # http://fr.wikipedia.org/wiki/Distance_du_grand_cercle
        def square(a): return a*a
        def degree_to_radian(a): return a * math.pi / 180
        a_lon = degree_to_radian(float(self.attrs["lon"]))
        a_lat = degree_to_radian(float(self.attrs["lat"]))
        b_lon = degree_to_radian(float(node.attrs["lon"]))
        b_lat = degree_to_radian(float(node.attrs["lat"]))
        R = 6371000.0 # Earth ray in metter
        result = 2 * R * math.asin(math.sqrt(
            square(math.sin((b_lat-a_lat)/2))
            + math.cos(a_lat)*math.cos(b_lat)*square(math.sin((b_lon-a_lon)/2))
            ));
        return result

class Way(Item):
    def __init__(self, attrs,tags=None):
        Item.__init__(self, attrs, tags)
        self.nodes = []
    def type(self):
        return "way"
    def add_node(self, node):
        if (type(node) == str) or (type(node) == unicode) or (type(node) == int):
            self.nodes.append(int(node))
        else:
            self.nodes.append(node.id())
        

class Relation(Item):
    def __init__(self, attrs,tags=None):
        Item.__init__(self, attrs, tags)
        self.members = []
    def type(self):
        return "relation"
    def add_member_type_ref_role(self, mtype, mref, mrole):
        attrs = {'type': mtype, 'ref': str(mref), 'role': mrole}
        self.add_member_attrs(attrs)
    def add_member(self, member, role=""):
        attrs = {'type': member.type(), 'ref': str(member.id()), 'role': role}
        self.add_member_attrs(attrs)
    def add_member_attrs(self, attrs):
        self.members.append(attrs)
    def itermembers(self):
        for attrs in self.members:
            yield attrs.get("type"), int(attrs.get("ref")), attrs.get("role")

class OsmParser(object):
    def __init__(self, factory=Osm):
        self.parser = xml.parsers.expat.ParserCreate("utf-8")
        assert(self.parser.SetParamEntityParsing(
            xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER))
        self.parser.buffer_text = True
        self.parser.CharacterDataHandler = self.handle_char_data
        self.parser.StartElementHandler = self.handle_start_element
        self.parser.EndElementHandler = self.handle_end_element
        self.factory = factory
    def parse(self, filename):
        self.filename = filename
        self.osm = None
        self.parser.ParseFile(open(filename))
        return self.osm
    def parse_stream(self, stream, name=""):
        self.filename = name
        self.osm = None
        self.parser.ParseFile(stream)
        return self.osm
    def parse_data(self, data, name=""):
        self.filename = name
        self.osm = None
        self.parser.Parse(data)
        return self.osm
    def handle_start_element(self,name, attrs):
        if name == "osm":
            osm = self.factory(attrs)
            self.osm = osm
            self.current = None
        elif name == "note":
            #TODO
            pass
        elif name == "meta":
            #TODO
            pass
        elif name == "bounds":
            self.osm.add_bounds(attrs)
        elif name == "node":
            node = self.osm.create_node(attrs);
            self.current = node
        elif name == "way":
            way = self.osm.create_way(attrs)
            self.current = way
        elif name == "nd":
            ref = int(attrs["ref"])
            way = self.current
            way.add_node(ref)
        elif name == "tag":
            self.current.tags[attrs["k"]] = attrs["v"];
        elif name == "relation":
            relation = self.osm.create_relation(attrs)
            self.current = relation
        elif name == "member":
            relation = self.current
            relation.add_member_attrs(attrs)
        else:
            raise Exception("ERROR: unknown tag <"+name+"> in file " 
                    + self.filename + "\n")
    def handle_end_element(self,name):
        pass
    def handle_char_data(self,data):
        pass
 
class OsmWriter(object):
    def __init__(self, osm):
        self.osm = osm
    def write_to_file(self, filename):
        self.output = open(filename, mode="w")
        self.write()
        self.output.close()
    def write_to_stream(self, stream):
        self.output = stream
        self.write()
    def write(self):
        osm = self.osm
        output = self.output
        output.write("<?xml version='1.0' encoding='UTF-8'?>\n");
        output.write("<osm" + self.attrs_str(osm.attrs) + ">\n");
        for bounds in osm.bounds:
            output.write("\t<bounds" + self.attrs_str(bounds) + "/>\n");
        for node in osm.nodes.itervalues():
            if len(node.tags):
                output.write("\t<node" + self.attrs_str(node.attrs) + ">\n");
                self.write_tags(node.tags)
                output.write("\t</node>\n");
            else:    
                output.write("\t<node" + self.attrs_str(node.attrs) + "/>\n");
        for way in osm.ways.itervalues():
            output.write("\t<way" + self.attrs_str(way.attrs) + ">\n");
            for ref_node in way.nodes:
                output.write('\t\t<nd ref="' + str(ref_node) + '"/>\n');
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
        return ("".join([' ' + key + '=' + xml.sax.saxutils.quoteattr(value)
            for key,value in attrs.iteritems()])).encode("utf-8")
    def write_tags(self, tags):
        for key,value in tags.iteritems():
            value = xml.sax.saxutils.quoteattr(value)
            self.output.write(('\t\t<tag k="' + key + '" v=' + value +'/>\n').encode("utf-8"))


