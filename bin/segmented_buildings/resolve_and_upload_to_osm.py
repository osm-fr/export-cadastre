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
 - try to resolve segmentation_cases from segmentation_contributions
   stored in the database.
 - upload to OpenStreetMap the building "join" operations that can be done
   automatically, and mark them as resolved
 - generate .osm files for "join" operations that need to be done manually
   or that are conflicting with other joins.
"""

import sys
import json
import math
import numpy
import os.path
import psycopg2
import numpy as np
from osmapi import OsmApi
from collections import namedtuple

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "cadastre-housenumber"))
from cadastre_fr.globals   import EARTH_RADIUS_IN_METER
from cadastre_fr.simplify  import xtd


VERBOSE=True
UPLOAD=True
DEFAULT_SIMPLIFY_THRESHOLD = 0.1
OSM_USERNAME = "FR-segmented-buildings"
OSM_PASSWORDFILE = os.path.join(os.path.dirname(sys.argv[0]), ".osm-password")

JoinCase = namedtuple("JoinCase", ["case_id", "way1_id", "way2_id", "osm_data"])
dbstring = file(os.path.join(os.path.dirname(sys.argv[0]), ".database-connection-string")).read()
db = psycopg2.connect(dbstring)
db.autocommit = True
cur = db.cursor()

api = OsmApi(username=OSM_USERNAME, passwordfile=OSM_PASSWORDFILE)

def main(args):
    resolve_undecided()
    cur.execute("""
        SELECT ca.id, co1.choice, way1_osm_id, ST_AsText(way1_geom), way2_osm_id, ST_AsText(way2_geom)
        FROM segmented_cases ca
        INNER JOIN segmented_contributions_rank co1
            ON (co1.case_id=ca.id)
        LEFT JOIN segmented_contributions_rank co2
            ON (co2.case_id=ca.id AND co2.rank>1)
        WHERE ca.resolution = 'none'
            AND co1.rank=1
            AND co1.nb>=3
        GROUP BY ca.id, co1.choice, co1.nb, co1.last
        HAVING co1.nb-coalesce(sum(co2.nb),0)>=3
        ORDER BY co1.last
    """)
    join_cases = {}
    for case_id, choice, way1_id, way1_geom, way2_id, way2_geom in cur.fetchall():
        print case_id, choice, way1_id, way2_id
        if choice in ["keep", "unknown"]:
            cur.execute(cur.mogrify("""
                UPDATE segmented_cases
                SET resolution=%s, resolution_time=now()
                WHERE id=%s""",(choice, case_id)));
        elif choice == "join":
            way1_geom, way2_geom = map(wkt_polygon_latlngs, (way1_geom, way2_geom))
            way1 = api.WayGet(way1_id)
            way2 = api.WayGet(way2_id)
            if (not way1) or (not way2):
                if not way1:
                    print "way1 ", way1_id, "already deleted"
                    cur.execute(cur.mogrify("""
                        UPDATE segmented_cases
                        SET resolution='outofdate', resolution_time=now()
                        WHERE resolution='none' AND (way1_osm_id=%s OR way2_osm_id=%s)""", (way1_id, way1_id)));
                if not way2:
                    print "way2 ", way2_id, "already deleted"
                    cur.execute(cur.mogrify("""
                        UPDATE segmented_cases
                        SET resolution='outofdate', resolution_time=now()
                        WHERE resolution='none' AND (way1_osm_id=%s OR way2_osm_id=%s)""", (way2_id, way2_id)));
            else:
                way1 = api.WayFull(way1_id)
                way2 = api.WayFull(way2_id)
                # api.WayFull is actually not returning relations as doc say, so also get relations:
                way1 = way1 + [{'type':'relation', 'data': r} for r in api.WayRelations(way1_id)]
                way2 = way2 + [{'type':'relation', 'data': r} for r in api.WayRelations(way2_id)]
                osm_data = osm_data_update(osm_data_by_type(way1), osm_data_by_type(way2))
                way1_osm_geom = osm_way_latlngs(osm_data, way1_id)
                way2_osm_geom = osm_way_latlngs(osm_data, way2_id)
                if latlngs_equals(way1_geom, way1_osm_geom) and latlngs_equals(way2_geom, way2_osm_geom):
                    join_cases[case_id] = JoinCase(case_id, way1_id, way2_id, osm_data)
                else:
                    print "way geometry changed, consider the case outofdate"
                    cur.execute(cur.mogrify("""
                        UPDATE segmented_cases
                        SET resolution='outofdate', resolution_time=now()
                        WHERE id=%s""", (case_id,)));
    excludes_cases_with_near_unresolved(join_cases)
    treat_join_cases(join_cases)


def try_join(case_id, way1_id, way2_id, osm_data):
    way1 = osm_data["way"][way1_id]
    way2 = osm_data["way"][way2_id]
    if VERBOSE: print "way1 nd", way1["nd"]
    if VERBOSE: print "way2 nd", way2["nd"]
    outer1, common, outer2 = join_node_list(way1["nd"], way2["nd"])
    if VERBOSE: print "outer1", outer1
    if VERBOSE: print "common", common
    if VERBOSE: print "outer2", outer2
    joined_nds = [common[0]] + outer1 + [common[-1]] + outer2 + [common[0]]
    deleted_nds = common[1:-1]
    automatic_join = True
    if len(osm_data["relation"]) > 0 or len(osm_data["relation"]) > 0:
        automatic_join = False
    elif way1["tag"] != way2["tag"]:
        automatic_join = False
    else:
        for nd in deleted_nd:
            if not can_delete_node(osm_data, nd, way1_id, way2_id):
                automatic_join = False
                break
    if automatic_join:
        if VERBOSE: print "automatic"
        # Try also to delete the linking common nodes if it form a flat angle:
        if (len(outer1) > 0) and (len(outer2) > 0):
            if can_simplify_node(osm_data, nd_first=outer1[-1], nd_middle=common[-1], nd_last=outer1[0]) and can_delete_node(osm_data, common[-1], way1_id, way2_id):
                if VERBOSE: print "delete last common node"
                deleted_nds = deleted_nds + [common[-1]]
                joined_nds = [common[0]] + outer1 + outer2 + [common[0]]

            if can_simplify_node(osm_data, nd_first=outer2[-1], nd_middle=common[0], nd_last=outer1[0]) and can_delete_node(osm_data, common[0], way1_id, way2_id):
                if VERBOSE: print "delete fist common node"
                deleted_nds =  [common[0]] +  deleted_nds
                joined_nds = joined_nds[1:-1] + [joined_nds[1]]
            pass

        joined_way, deleted_way = [way1,way2] if len(way1)>len(way2) else [way2, way1]
        joined_way["nd"] = joined_nds
        modify_way(osm_data, joined_way["id"])
        delete_way(osm_data, deleted_way["id"])

        deleted_way["action"] = "delete"
        deleted_way["visible"] = "true"
        for nd in deleted_nds:
            delete_node(osm_data, nd)
    return automatic_join, osm_data


def treat_join_cases(join_cases):
    # look for conflict cases (cases sharing the same ways to join)
    way_case_ids = {}
    for join_case in join_cases.itervalues():
        add_map_set(way_case_ids, join_case.way1_id, join_case.case_id)
        add_map_set(way_case_ids, join_case.way2_id, join_case.case_id)
    cases_done = set()
    for case_id, join_case in join_cases.iteritems():
        if not case_id in cases_done:
            print "treat join case ", case_id
            conflict_cases = set([case_id])
            ways_to_add = [join_case.way1_id, join_case.way2_id]
            while len(ways_to_add) > 0:
                w = ways_to_add.pop()
                for c in way_case_ids[w]:
                    if not c in conflict_cases:
                        conflict_cases.add(c)
                        ways_to_add.append(join_cases[c].way1_id)
                        ways_to_add.append(join_cases[c].way2_id)
            if len(conflict_cases) > 1:
                osm_data = result = {"way":{}, "relation":{}, "node":{}}
                filename = "conflict"
                for c in conflict_cases:
                    cases_done.add(c)
                    osm_data = osm_data_update(osm_data, join_cases[c].osm_data)
                    filename = filename + "-%d" % c
                filename = filename + ".osm"
            else:
                cases_done.add(case_id)
                automatic, osm_data = try_join(join_case.case_id, join_case.way1_id, join_case.way2_id, join_case.osm_data)
                if automatic:
                    if UPLOAD:
                        filename = None
                        osm_upload(osm_data, source="https://cadastre.openstreetmap.fr/segmented/#%d" % (case_id,))
                        cur.execute(cur.mogrify("""UPDATE segmented_cases SET resolution='join', resolution_time=now() WHERE id=%s""", (case_id,)))
                    else:
                        filename = "automatic-%d.osm" % case_id
                else:
                    filename = "manual-%d.osm" % case_id
            if filename:
                print filename
                f = open(filename, "w")
                write_josm(osm_data, f)
                f.close()

def excludes_cases_with_near_unresolved(join_cases):
    """Excludes cases that have unresolved case near them
       as there may exist "join" conflicts between them
       that would not be detected from the join_cases list.
    """
    for join_case in list(join_cases.values()):
        cur.execute(cur.mogrify("""
            SELECT ca2.id
            FROM segmented_cases ca1, segmented_cases ca2
            WHERE   ca1.id=%s
                AND ca2.resolution = 'none'
                AND ST_Distance(ca1.center::geography, ca2.center::geography) < 200
                AND ST_Distance(
                        ST_Union(ca1.way1_geom, ca1.way2_geom)::geography,
                        ST_Union(ca2.way1_geom, ca2.way2_geom)::geography
                    ) < 5
            """, (join_case.case_id,)))
        for (near_case_id,) in cur.fetchall():
            if not near_case_id in join_cases:
                if VERBOSE: print "exclude case ", join_case.case_id," because of near unresolved case ", near_case_id
                del(join_cases[join_case.case_id])
                break


def resolve_undecided():
    """ mark as undecided cases having at leas 10 contributions but no majority choice. """
    cur.execute("""
        UPDATE segmented_cases
        SET resolution='undecided', resolution_time=now()
        WHERE resolution='none'
            AND id IN (
                SELECT c1.case_id
                FROM (segmented_contributions_rank c1
                LEFT JOIN segmented_contributions_rank c2 ON (((c2.case_id = c1.case_id) AND (c2.rank > 1))))
                WHERE (c1.rank = 1)
                GROUP BY c1.case_id, c1.choice, c1.nb
                HAVING (((c1.nb)::numeric - COALESCE(sum(c2.nb), (0)::numeric)) < (3)::numeric)
                    AND ((c1.nb)::numeric + COALESCE(sum(c2.nb), (0)::numeric)) >= 10
        );""")

def osm_data_by_type(data):
    result = {"way":{}, "relation":{}, "node":{}}
    for item in data:
        result[item["type"]][item["data"]["id"]] = item["data"]
    return result

def osm_data_update(data, update):
    if type(update) == list: update = osm_data_by_type(update)
    for key in data.keys():
        data[key].update(update[key])
    return data

def osm_way_latlngs(data, id):
    return [(data["node"][nd]["lat"], data["node"][nd]["lon"]) for nd in data["way"][id]["nd"]]

def wkt_polygon_latlngs(wkt):
    assert(wkt.startswith("POLYGON((") and wkt.endswith("))"));
    coords = wkt[len("POLYGON(("): -len("))")];
    return [map(float,p.split(" ")) for p in  coords.split(",")]

def latlngs_equals(latlngs1, latlngs2):
    if len(latlngs1) == len(latlngs2):
        diff = np.array(latlngs1) - np.array(latlngs2)
        return np.max(np.abs(diff)) < 0.0000001
    else:
        return False

def find(list_element, element):
    try:
        return list_element.index(element)
    except ValueError:
        return None

def shift_to_common_start_and_get_common_size(l1, l2):
    swaped = False
    if len(l1)<len(l2):
        # To find the first common start, our algo look for an
        # item of l1 not member of l2, but if all l1 is member of l2
        # it wont exist, so we swap them to be sure:
        l1,l2 = l2,l1
        swaped = True
    size1 = len(l1)
    size2 = len(l2)
    i1 = 0
    prev_i1 = size1 - 1
    while i1 < size1:
        i2 = find(l2, l1[i1])
        if (i2 != None) and (find(l2, l1[prev_i1]) == None):
            if l2[(i2-1+size2)%size2] == l1[(i1+1)%size1]:
                l2.reverse()
                i2 = size2 - 1 - i2;
            l1 = l1[i1:] + l1[:i1]
            l2 = l2[i2:] + l2[:i2]
            break;
        prev_i1 = i1;
        i1 = i1+1
    common_size = 0;
    while (common_size < size1) and (common_size < size2) and (l1[common_size] == l2[common_size]):
            common_size = common_size + 1;
    if swaped:
        l1,l2 = l2,l1
    return l1, l2, common_size

def deg_to_rad(a): return a*math.pi / 180
def rad_t_deg(a): return a*180/math.pi

def join_node_list(way1_nds, way2_nds):
    assert(way1_nds[0] == way1_nds[-1])
    assert(way2_nds[0] == way2_nds[-1])
    l1, l2, common_size = shift_to_common_start_and_get_common_size(way1_nds[:-1], way2_nds[:-1])
    outer1 = l1[common_size:]
    outer2 = l2[common_size:]
    common = l1[:common_size]
    outer2.reverse()
    common.reverse()
    return outer1, common, outer2

def add_map_set(map_list, key, item):
    if not key in map_list:
        map_list[key] = set()
    map_list[key].add(item)

def osm_changeset_open(comment=None, source=None):
    if comment == None:
        comment = "Merge segmented building"
    if source == None:
        source = "https://cadastre.openstreetmap.fr/segmented/"
    changeset = api.ChangesetCreate({"comment": comment, "source": source})
    if VERBOSE: print "opened changeset ", changeset
    return changeset

def osm_changeset_close():
    changeset = api.ChangesetClose()
    print "closed changeset ", changeset
    api.flush()

def osm_upload(osm_data, source=None):
    osm_changeset_open(source=source)
    for way in osm_data["way"].values():
        if "action" in way:
            if way["action"] == "modify":
                api.WayUpdate({k:v for k,v in way.iteritems() if k!="action"})
            if way["action"] == "delete":
                api.WayDelete({k:v for k,v in way.iteritems() if k!="action"})
    for node in osm_data["node"].values():
        if "action" in node:
            if node["action"] == "delete":
                api.NodeDelete({k:v for k,v in node.iteritems() if k!="action"})
    osm_changeset_close()


max_id = 0;
def new_id():
    global max_id
    max_id = max_id + 1
    return -max_id

def can_simplify_node(osm_data, nd_first, nd_last, nd_middle):
    nd1, nd2, nd3 = [osm_data["node"][nd] for nd in nd_first, nd_last, nd_middle]
    coords = nd1["lat"], nd1["lon"], nd2["lat"], nd2["lon"], nd3["lat"], nd3["lon"]
    coords = map(deg_to_rad, coords)
    xte = abs(EARTH_RADIUS_IN_METER * xtd(*coords))
    if VERBOSE: print "xte = ", xte
    return xte < DEFAULT_SIMPLIFY_THRESHOLD

def can_delete_node(osm_data, nd, way1_id, way2_id):
    node_ways = [w for w in api.NodeWays(nd) if w["id"] not in (way1_id, way2_id)]
    return (len(osm_data["node"][nd]["tag"]) == 0) and (len(node_ways) == 0) and (len(api.NodeRelations(nd)) == 0)

def delete_node(osm_data, node_id):
    print "delete node", node_id
    osm_data["node"][node_id]["action"] = "delete"

def create_node(osm_data, node):
    node["id"] = new_id()
    node["action"] = "modify"
    node["visible"] = "true"
    osm_data[node["id"]] = node

def modify_way(osm_data, way_id):
    if VERBOSE: print "modify way", way_id
    osm_data["way"][way_id]["action"] = "modify"

def delete_way(osm_data, way_id):
    if VERBOSE: print "delete way", way_id
    osm_data["way"][way_id]["action"] = "delete"
    osm_data["way"][way_id]["nd"] = []


def write_josm_tags(item, output):
    for key,value in item["tag"].iteritems():
        output.write((u"    <tag k='%s' v='%s' />\n" % (key,value)).encode("utf-8"))

def write_josm_keys(item, output):
    for key,value in item.iteritems():
        if not key in ['tag', 'nd', 'member', 'timestamp']:
            output.write((u" %s='%s'" % (key,value)).encode("utf-8"))

def write_josm(osm_data, output):
    output.write("<?xml version='1.0' encoding='UTF-8'?>\n");
    output.write("<osm version='0.6' upload='true' generater='%s'>\n" % sys.argv[0]);
    for item in osm_data["node"].itervalues():
        output.write("  <node ")
        write_josm_keys(item, output)
        output.write(">\n");
        write_josm_tags(item, output)
        output.write("  </node>\n")
    for item in osm_data["way"].itervalues():
        output.write("  <way ")
        write_josm_keys(item, output)
        output.write(">\n");
        for nd in item["nd"]:
            output.write("    <nd ref='%s' />\n" % nd)
        write_josm_tags(item, output)
        output.write("  </way>\n")
    for item in osm_data["relation"].itervalues():
        output.write("  <relation ")
        write_josm_keys(item, output)
        output.write(">\n");
        write_josm_tags(item, output)
        for member in item["member"]:
            output.write(u"    <member ")
            write_josm_keys(member, output)
            output.write(" />\n")
        output.write("  </relation>\n")
    output.write("</osm>\n");
    output.flush()

if __name__ == '__main__':
    main(sys.argv[1:])

