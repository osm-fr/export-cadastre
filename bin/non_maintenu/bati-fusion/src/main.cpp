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

#include <iostream>
#include <fstream>
#include "OSMDocument.h"

int main(int argc, char * const argv[]) 
{
   if (argc != 4)
   {
      std::cerr << "Utilisation: " << argv[0] << " calque-bati calque-courant prefixe-sortie" << std::endl;
      return 1;
   }
   
   std::cout << "Chargement de " << argv[1] << "..." << std::endl;
   OSMDocument *osmBatiDoc = new OSMDocument(argv[1]);
   
   std::cout << "Chargement de " << argv[2] << "..." << std::endl;
   OSMDocument *osmCurrent = new OSMDocument(argv[2]);
   
   batiFusion(*osmBatiDoc, *osmCurrent, argv[3]);
   
   delete osmBatiDoc;
   delete osmCurrent;
}
