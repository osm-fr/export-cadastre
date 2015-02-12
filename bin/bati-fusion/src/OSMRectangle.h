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

#ifndef OSM_RECTANGLE_H
#define OSM_RECTANGLE_H

#include "OSMNode.h"
#include <math.h>

class OSMRectangle
{
public:
   
   OSMRectangle(const double x1, const double y1, const double x2, const double y2);
   
   double getArea() const { return (fabs(p1.getX()-p2.getX()) * fabs(p1.getY()-p2.getY())); }
   
   bool isZero() const { return ((p1.getX() == 0) && (p1.getY() == 0) && (p2.getX() == 0) && (p2.getY() == 0)); }
   
   const OSMNode & getP1() const { return p1; }
   const OSMNode & getP2() const { return p2; }
   
   friend OSMRectangle intersection(const OSMRectangle & r1, const OSMRectangle & r2);
   friend std::ostream & operator<<(std::ostream & os, const OSMRectangle & r);
   
private:
   OSMNode p1, p2;
};

OSMRectangle intersection(const OSMRectangle & r1, const OSMRectangle & r2);

std::ostream & operator<<(std::ostream & os, const OSMRectangle & r);


#endif