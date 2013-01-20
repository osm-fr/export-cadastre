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

#ifndef OSM_NODE_H
#define OSM_NODE_H

#include "tinyxml.h"
#include <map>
#include <string>

class OSMNode
{
public:
   typedef std::map<std::string, std::string> TagsContainer;
   typedef TagsContainer::const_iterator      TagsConstIterator;
   typedef TagsContainer::iterator            TagsIterator;
   
   OSMNode(const double x, const double y);
   OSMNode(TiXmlElement *element);
   
   OSMNode(const OSMNode & original);
   OSMNode & operator=(const OSMNode & original);
   ~OSMNode();
   
   int getID() const            { return id;  }
   void setID(const int value)  { id = value; }
   
   double getX() const { return x; }
   double getY() const { return y; }
   
   void setX(const double value) {x = value; }
   void setY(const double value) {y = value; }
   
   void dumpOSM(std::ostream & os);   
   
   TagsConstIterator getTagsBegin() const { return tags.begin(); }
   TagsConstIterator getTagsEnd() const   { return tags.end();   }
   
   void importTags(const OSMNode & original, bool avoidSource);
   
   friend std::ostream & operator<<(std::ostream & os, const OSMNode & node);
   friend double squareDistance(const OSMNode & op1, const OSMNode & op2);
   
private:
   int           id;
   double        x;
   double        y;
   std::string  *x_string;
   std::string  *y_string;
   TagsContainer tags;
   
   void clone(const OSMNode & original);
   void destroy();
};

std::ostream & operator<<(std::ostream & os, const OSMNode & node);

double squareDistance(const OSMNode & op1, const OSMNode & op2);

#endif
