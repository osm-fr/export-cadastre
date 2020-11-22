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

#ifndef OSM_DOCUMENT_H
#define OSM_DOCUMENT_H

#include <map>
#include "OSMNode.h"
#include "OSMWay.h"
#include "OSMRelation.h"

class OSMDocument
{
public:
   typedef std::map<int, OSMNode *>           NodesContainer;
   typedef NodesContainer::const_iterator     NodesConstIterator;
   typedef NodesContainer::iterator           NodesIterator;
   
   typedef std::map<int, OSMWay *>            WaysContainer;
   typedef WaysContainer::const_iterator      WaysConstIterator;
   typedef WaysContainer::iterator            WaysIterator;
   
   typedef std::map<int, OSMRelation *>       RelationsContainer;
   typedef RelationsContainer::const_iterator RelationsConstIterator;
   typedef RelationsContainer::iterator       RelationsIterator;
   
   OSMDocument();
   OSMDocument(const char * filename);
   
   ~OSMDocument();
   
   // Add a new way to the document by copying everything in way
   OSMWay & addWay(const OSMWay & way);
   // Same as addWay, but by also copying multipolygon relations and members
   OSMWay & addWay(const OSMWay & way, const OSMDocument & owner);
   
   OSMWay & addRectangle(const OSMRectangle & rect);
   
   void addNodePointerUID(OSMNode * node);
   void addWayPointerUID(OSMWay * way);
   
   void dumpOSM(const std::string & filename) const;
   
   void dumpBoundingBoxes(const std::string & filename) const;
   
   friend void batiFusion(const OSMDocument & bati, const OSMDocument & current, const std::string & outputPrefix);
   
private:
   NodesContainer     nodes;
   WaysContainer      ways;
   RelationsContainer relations;
};

void batiFusion(const OSMDocument & bati, const OSMDocument & current, const std::string & outputPrefix);
void tagFusion(const OSMWay & source, OSMWay & destination);

#endif
