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

#include "OSMNode.h"
#include <iostream>
#include <stdexcept>
#include <iomanip>
#include "utils.h"

OSMNode::OSMNode(const double x_, const double y_) :
  id(0),
  x(x_),
  y(y_),
  x_string(0),
  y_string(0)
{
}

OSMNode::OSMNode(TiXmlElement *element) :
  id(0),
  x(0),
  y(0),
  x_string(0),
  y_string(0)
{
   if (element->Value() != std::string("node"))
   {
      std::cerr << "Unexpected '" << element->Value() << "' XML node, expected 'node'" << std::endl;
      throw std::runtime_error("wrong node");
   }
   
   element->QueryIntAttribute("id", &id);
   element->QueryDoubleAttribute("lat", &y);
   element->QueryDoubleAttribute("lon", &x);
   
   std::string lx_string, ly_string;
   element->QueryStringAttribute("lat", &ly_string);
   element->QueryStringAttribute("lon", &lx_string);
   
   x_string = new std::string(lx_string);
   y_string = new std::string(ly_string);
   
   //std::cout << "id: " << id << " lat_precision: " << y_string.size()-1 << std::endl;
   //std::cout << "id: " << m_id  << " x: " <<x << " y: " << y << std::endl;
   
   TiXmlHandle refH(element);
   TiXmlElement *ref = refH.FirstChild().Element();
   
   for (; ref; ref=ref->NextSiblingElement())
   {   
      if (ref->Value() == std::string("tag"))
      {
         std::string key, value;
         ref->QueryStringAttribute("k", &key);
         ref->QueryStringAttribute("v", &value);      
         
         if (!key.empty() && !value.empty())
         {
            //std::cout << "Reading key: " << key << " value: " << value << std::endl;
           tags[key] = value;
         }
      }
   }
}

void OSMNode::destroy()
{
   delete x_string; x_string = 0;
   delete y_string; y_string = 0;
}

void OSMNode::clone(const OSMNode & original)
{
   id = original.id;
   x = original.x;
   y = original.y;
   
   if (original.x_string)
      x_string = new std::string(*original.x_string);
   
   if (original.y_string)
      y_string = new std::string(*original.y_string);
   
   tags = original.tags;
}

OSMNode::OSMNode(const OSMNode & original)
{
   clone(original);
}

OSMNode & OSMNode::operator=(const OSMNode & original)
{
   destroy();
   clone(original);
   
   return *this;
}

OSMNode::~OSMNode()
{
   destroy();
}

void OSMNode::dumpOSM(std::ostream & os)
{      
   os << "  <node id='" << id;
   os << "' visible='true' lat='";
   
   if (y_string)
      os << *y_string;
   else 
      os << y;

   os << "' lon='";
   
   if (x_string)
      os << *x_string;
   else
      os << x;
   
   os << "'";
   
   if (tags.empty())
      os << " />\n";
   else 
   {
      os << ">\n";
      
      for (std::map<std::string, std::string>::const_iterator it = tags.begin(); it != tags.end(); ++it)
      {
         os << "    <tag k='" << (*it).first << "' v='" << escape_xml_char((*it).second) << "' />\n";
      }
      os << "  </node>\n";
   }
}

void OSMNode::importTags(const OSMNode & original, bool avoidSource)
{
   // Import tags of way itself
   for (TagsConstIterator it = original.tags.begin(); it != original.tags.end(); ++it)
   {
      // If tags does not already exist in destination
      if (tags.find((*it).first) == tags.end())
      {
         if (avoidSource && ((*it).first == "source"))
            continue;
         
         tags[(*it).first] = (*it).second;
      }
   }
}

std::ostream & operator<<(std::ostream & os, const OSMNode & node)
{
   return os << node.x << ", " << node.y;
}

double squareDistance(const OSMNode & op1, const OSMNode & op2)
{
   return ( (op1.x-op2.x)*(op1.x-op2.x) + (op1.y-op2.y)*(op1.y-op2.y) );
}
