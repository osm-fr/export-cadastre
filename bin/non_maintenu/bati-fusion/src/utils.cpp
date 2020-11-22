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

#include "utils.h"

void try_escape(std::string & source, const char fchar, const char *escape_sequence)
{
   std::string::size_type pos;
   
   while ((pos = source.find(fchar)) != std::string::npos)
   {
      source.replace(pos, 1, escape_sequence);
   }
}

std::string escape_xml_char(const std::string & str)
{
   std::string ret(str);
   
   try_escape(ret, '&', "&amp;");
   try_escape(ret, '<', "&lt;");
   try_escape(ret, '>', "&gt;");
   try_escape(ret, '"', "&quot;");
   try_escape(ret, '\'', "&apos;");
   
   return ret;
}