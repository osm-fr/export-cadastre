/*
 * bati-fusion - Utilitaire de fusion Open Street Map  
 * Copyright (c) 2010-2011 Jérôme Cornet
 * 
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef OSM_WAY_H
#define OSM_WAY_H

#include <map>
#include <vector>
#include "tinyxml.h"
#include "OSMNode.h"
#include "OSMRectangle.h"

class OSMWay
{
public:
   typedef std::vector<OSMNode *>             NodesContainer;
   typedef NodesContainer::const_iterator     NodesConstIterator;
   typedef NodesContainer::iterator           NodesIterator;
   
   typedef std::map<std::string, std::string> TagsContainer;
   typedef TagsContainer::const_iterator      TagsConstIterator;
   typedef TagsContainer::iterator            TagsIterator;
   
   
   OSMWay();
   
   OSMWay(const std::map<int, OSMNode *> & nodes, TiXmlElement * element);
   OSMWay(const OSMWay & way);
   
   int getID() const           { return id;  }
   void setID(const int value) { id = value; }
   
   OSMRectangle getBoundingBox() const;
   
   bool isBuilding() const { return building; }
   
   unsigned int getNbNodes() const { return nodes.size(); }
   
   OSMNode & getNode(const unsigned int index) const { return *nodes[index]; }
   
   void addNodePointer(OSMNode * node);
   
   void dumpOSM(std::ostream & os);
   
   void importTags(const OSMWay & original, bool avoidSource);
   
private:
   int            id;
   bool           building;
   NodesContainer nodes;
   TagsContainer  tags;
};

#endif