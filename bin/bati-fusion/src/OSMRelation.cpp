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

#include "OSMRelation.h"
#include <stdexcept>
#include <iostream>
#include "utils.h"

OSMRelation::OSMRelation()
{
}

OSMRelation::OSMRelation(const std::map<int, OSMWay *> & input_ways, TiXmlElement * element) :
id(0)
{
   if (element->Value() != std::string("relation"))
   {
      std::cerr << "Unexpected '" << element->Value() << "' XML node, expected 'relation'" << std::endl;
      throw std::runtime_error("wrong relation");
   }
   
   element->QueryIntAttribute("id", &id);
   
   TiXmlHandle refH(element);
   TiXmlElement *ref = refH.FirstChild().Element();
   
   for (; ref; ref=ref->NextSiblingElement())
   {
      if (ref->Value() == std::string("member"))
      {
         int refID = 0;
         ref->QueryIntAttribute("ref", &refID);
         
         std::map<int, OSMWay *>::const_iterator it = input_ways.find(refID);
         if (it != input_ways.end())
         {
            std::string role;
            
            ref->QueryStringAttribute("role", &role);
            
            members.push_back(std::make_pair(role, (*it).second));
         }
         else 
         {
            // This is actually not an error, and very possible when extracting
            // part of the database
            
            /*std::cerr << "Way id " << refID << " not found in the list of ways!" << std::endl;
            throw std::runtime_error("way id not found");*/
         }
      }
      else if (ref->Value() == std::string("tag"))
      {
         std::string key, value;
         ref->QueryStringAttribute("k", &key);
         ref->QueryStringAttribute("v", &value);      
         
         if (!key.empty() && !value.empty())
         {
            //std::cout << "Way Reading key: " << key << " value: " << value << std::endl;
            tags[key] = value;
         }         
      }
   }
}

bool OSMRelation::isMultipolygon() const
{
   TagsConstIterator it;
   
   for (it = tags.begin(); it != tags.end(); ++it)
   {
      if (((*it).first == std::string("type") &&
           (*it).second == std::string("multipolygon")))
      {
         return true;
      }
   }
   
   return false;
}

bool OSMRelation::refers(const std::string & role, const OSMWay & way) const
{
   for (MembersConstIterator it = members.begin(); it != members.end(); ++it)
   {
      if (((*it).first == role) && ((*it).second == &way))
         return true;
   }
   
   return false;
}

void OSMRelation::addMemberPointer(const std::string & role, OSMWay *way)
{
   members.push_back(std::make_pair(role, way));
}

void OSMRelation::dumpOSM(std::ostream & os)
{
   os << "  <relation id='" << id << "' visible='true'>\n";
   
   for (MembersConstIterator it = members.begin(); it != members.end(); ++it)
   {
      os << "    <member type='way' ref='" << ((*it).second)->getID() << "' role='" << (*it).first << "' />\n";
   }
   
   for (TagsConstIterator it = tags.begin(); it != tags.end(); ++it)
   {
      os << "    <tag k='" << (*it).first << "' v='" << escape_xml_char((*it).second) << "' />\n";
   }
   
   os << "  </relation>\n";
}


