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

#include "OSMDocument.h"
#include "OSMNode.h"
#include "OSMWay.h"
#include <stdexcept>
#include <iostream>
#include <fstream>
#include <iomanip>
#include "tinyxml.h"

const double kThresholdOK    = 0.80;
const double kThresholdDoubt = 0.50;
const double kThresholdNoFusion = 0.10;

OSMDocument::OSMDocument()
{
}

OSMDocument::OSMDocument(const char * filename)
{
   TiXmlDocument  doc(filename);
   TiXmlHandle    hDoc(&doc);
   TiXmlHandle    hRoot(0);
   TiXmlElement   *element;
   
   doc.LoadFile();
   
   element = hDoc.FirstChildElement().Element();
   if (!element)
   {
      std::cerr << "Did not find root element in osm file!" << std::endl;
      
      throw std::runtime_error("root element not found");
   }
   if (element->Value() != std::string("osm"))
   {
      std::cerr << "Unexpected root '" << element->Value() << "' in osm file, expected 'osm'." << std::endl;
      
      throw std::runtime_error("unexpected root");
   }
   
   hRoot = TiXmlHandle(element);
   
   element = hRoot.FirstChild().Element();
   for (; element; element=element->NextSiblingElement())
   {
      if (element->Value() == std::string("node"))
      {
         OSMNode *node = new OSMNode(element);
         
         nodes[node->getID()] = node;
      }
      else if (element->Value() == std::string("way"))
      {
         OSMWay *way = new OSMWay(nodes, element);
         
         //if (way->isBuilding())
            ways[way->getID()] = way;
      }
      else if (element->Value() == std::string("relation"))
      {
         OSMRelation *relation = new OSMRelation(ways, element);
         
         if (relation->isMultipolygon())
            relations[relation->getID()] = relation;
      }
   }
}

OSMDocument::~OSMDocument()
{
   for (NodesConstIterator it = nodes.begin(); it != nodes.end(); ++it)
   {
      delete (*it).second;
   }
   
   for (WaysConstIterator it = ways.begin(); it != ways.end(); ++it)
   {
      delete (*it).second;
   }
   
   for (RelationsConstIterator it = relations.begin(); it != relations.end(); ++it)
   {
      delete (*it).second;
   }
}

OSMWay & OSMDocument::addWay(const OSMWay & way)
{
   OSMWay *myway = new OSMWay(way);
   
   for (size_t i=0; i<myway->getNbNodes(); i++)
   {
      OSMNode & node = myway->getNode(i);
         
      nodes[node.getID()] = &node;
   }
   ways[myway->getID()] = myway;
   
   return *myway;
}

OSMWay & OSMDocument::addWay(const OSMWay & way, const OSMDocument & owner)
{
   OSMWay & ret = addWay(way);
   
   for (RelationsConstIterator it = owner.relations.begin(); it != owner.relations.end(); ++it)
   {
      const OSMRelation & relation = *(*it).second;
      
      if (relation.isMultipolygon() && relation.refers("outer", way))
      {
         OSMRelation *newrelation = new OSMRelation;
         
         newrelation->precopy(relation);
         
         for (unsigned int i = 0; i < relation.getNbMembers(); i++)
         {
            const std::pair<std::string, OSMWay *> & member = relation.getMember(i);
            
            OSMWay & myway = addWay(*member.second);
            
            newrelation->addMemberPointer(member.first, &myway);
         }
         
         relations[newrelation->getID()] = newrelation;
      }
   }
   
   return ret;
}

OSMWay & OSMDocument::addRectangle(const OSMRectangle & rect)
{
   OSMNode *p1 = new OSMNode(rect.getP1());
   OSMNode *p2 = new OSMNode(rect.getP2());
   
   OSMNode *p12 = new OSMNode(p1->getX(), p2->getY());
   OSMNode *p21 = new OSMNode(p2->getX(), p1->getY());
   
   addNodePointerUID(p1);
   addNodePointerUID(p2);
   addNodePointerUID(p12);
   addNodePointerUID(p21);
   
   OSMWay *way = new OSMWay;
   
   way->addNodePointer(p1);
   way->addNodePointer(p12);
   way->addNodePointer(p2);
   way->addNodePointer(p21);
   way->addNodePointer(p1);
   
   addWayPointerUID(way);
   
   return *way;
}

void OSMDocument::addNodePointerUID(OSMNode * node)
{
   int newID = -1;
   
   while ((nodes.find(newID) != nodes.end()) ||
          (ways.find(newID) != ways.end()))
   {
      newID--;
   }
   
   node->setID(newID);
   nodes[newID] = node;
}

void OSMDocument::addWayPointerUID(OSMWay * way)
{
   int newID = -1;
   
   while ((ways.find(newID) != ways.end()) ||
          (nodes.find(newID) != nodes.end()))
   {
      newID--;
   }
   
   way->setID(newID);
   ways[newID] = way;
}

void OSMDocument::dumpOSM(const std::string & fileName) const
{
   std::ofstream os(fileName.c_str());
   
   if (os)
   {
      //os.exceptions(os.badbit | os.failbit);
      
      try 
      {
         os << "<?xml version='1.0' encoding='UTF-8'?>\n";
         os << "<osm version='0.6' generator='bati-fusion'>\n";
         
         for (NodesConstIterator it = nodes.begin(); it != nodes.end(); ++it)
         {
            (*it).second->dumpOSM(os);
         }
                  
         for (WaysConstIterator it = ways.begin(); it != ways.end(); ++it)
         {
            (*it).second->dumpOSM(os);
         }
         
         for (RelationsConstIterator it = relations.begin(); it != relations.end(); ++it)
         {
            (*it).second->dumpOSM(os);
         }
         
         os << "</osm>" << std::endl;
      }
      catch (const std::ofstream::failure & e)
      {
         std::cerr << "Failure: " << e.what() << std::endl;
      }
      catch (std::exception & e)
      {
         std::cerr << "Exception: " << e.what() << std::endl;
      }
   }
   else 
   {
      std::cerr << "Unable to open output file '" << fileName << "'!" << std::endl;
   }

   os.close();
}

void OSMDocument::dumpBoundingBoxes(const std::string & filename) const
{
   OSMDocument *boundingDoc = new OSMDocument;
   
   std::vector<OSMRectangle> boundingBoxes;
   
   // Compute all bounding boxes
   for (WaysConstIterator it = ways.begin(); it != ways.end(); ++it)
   {
      boundingDoc->addRectangle((*it).second->getBoundingBox());
   }
                           
   boundingDoc->dumpOSM(filename);
   
   delete boundingDoc;
}
                              


/*void checkOverlap(const OSMDocument & d1, const OSMDocument & d2)
{
   for (std::map<int, OSMWay *>::const_iterator itd2 = d2.ways.begin(); itd2 != d2.ways.end(); ++itd2)
   {
      for (std::map<int, OSMWay *>::const_iterator itd1 = d1.ways.begin(); itd1 != d1.ways.end(); ++itd1)
      {
         const OSMWay & w1 = *(*itd1).second;
         const OSMWay & w2 = *(*itd2).second;
         OSMRectangle r = intersection(w1.getBoundingBox(), w2.getBoundingBox());
         
         if (!r.isZero())
         {
            std::cout << "d1 way id " << w1.getID() << " overlaps with d2 way id " << w2.getID() << " (";
            std::cout << (r.getArea() / w2.getBoundingBox().getArea())*100.0 << "%)" << std::endl;
         }
      }
   }
}*/



void batiFusion(const OSMDocument & bati, const OSMDocument & current, const std::string & outputPrefix)
{
   std::cout << "Fusion..." << std::endl;
   
   OSMDocument *okDoc = new OSMDocument;
   OSMDocument *noFusionDoc = new OSMDocument;
   OSMDocument *fusionDoc = new OSMDocument;
   OSMDocument *conflitDoc = new OSMDocument;
   
   unsigned int nbOK = 0;
   unsigned int nbNoFusion = 0;
   unsigned int nbFusion = 0;
   unsigned int nbConflit = 0;
   
   
   for (std::map<int, OSMWay *>::const_iterator itBati = bati.ways.begin(); itBati != bati.ways.end(); ++itBati)
   {
      const OSMWay & batiWay = *(*itBati).second;
      
      if (batiWay.isBuilding())
      {
         std::vector<std::pair<const OSMWay *, double> > intersections;
         
         bool firstDisplay = true;
         
         for (std::map<int, OSMWay *>::const_iterator itCurrent = current.ways.begin(); itCurrent != current.ways.end(); ++itCurrent)
         {
            const OSMWay & currentWay = *(*itCurrent).second;
            
            if (currentWay.isBuilding())
            {
               OSMRectangle r = intersection(currentWay.getBoundingBox(), batiWay.getBoundingBox());
               
               //std::cout << "intersection de bati id " << batiWay.getID() << " et current id " << currentWay.getID();
               //std::cout << ": " << r << std::endl;
               
               if (!r.isZero())
               {
                  double overlap = r.getArea()/std::max(batiWay.getBoundingBox().getArea(),
                                                        currentWay.getBoundingBox().getArea());
                  
                  intersections.push_back(std::make_pair(&currentWay, overlap));
                  
                  //std::cout << " aire: " << r.getArea();
                  //std::cout << " recouvrement: " << (unsigned int)((r.getArea()/batiWay.getBoundingBox().getArea())*100);
                  
                  if (firstDisplay)
                  {
                     firstDisplay = false;
                     std::cout << "Bati ID " << batiWay.getID() << ", intersection avec: " << std::endl;
                  }
                  std::cout << std::fixed << std::setprecision(2);
                  std::cout << " - current ID " << currentWay.getID() << ", recouvrement: " << overlap*100 << "%" << std::endl; 
               }
               //std::cout << std::endl;
            }
         }
         
         if (intersections.size() == 0)
         {
            okDoc->addWay(batiWay, bati);
            nbOK++;
         }
         else if ((intersections.size() == 1) && (intersections[0].second > kThresholdOK))
         {
            OSMWay & fusionWay = fusionDoc->addWay(batiWay, bati);
            
            fusionWay.importTags(*intersections[0].first, true);
            nbFusion++;
         }
         else if (intersections.size() > 1)
         {
            unsigned int nbThresholdOK = 0;
            unsigned int nbThresholdDoubt = 0;
            bool noFusion = true;
            size_t candidateIndex = 0;
            size_t maxIndex = 0;
            double maxValue = 0;
            
            for (size_t i=0; i<intersections.size(); i++)
            {
               if (intersections[i].second > kThresholdOK)
               {
                  nbThresholdOK++;
                  candidateIndex = i;
               }
               else if (intersections[i].second > kThresholdDoubt)
               {
                  nbThresholdDoubt++;
               }
               
               if (intersections[i].second > kThresholdNoFusion)
                  noFusion = false;
               
               if (intersections[i].second > maxValue)
               {
                  maxValue = intersections[i].second;
                  maxIndex = i;
               }
            }
            
            if (noFusion)
            {
               // No need to import tags, as a corresponding polygon
               // does not exist in current
               noFusionDoc->addWay(batiWay, bati);
               nbNoFusion++;
            }
            else if ((nbThresholdOK == 1) && (nbThresholdDoubt == 0))
            {
               OSMWay & fusionWay = fusionDoc->addWay(batiWay, bati);
               
               fusionWay.importTags(*intersections[candidateIndex].first, true);
               nbFusion++;
            }
            else
            {
               std::cout << "Conflit - way OK: " << nbThresholdOK << " - way doute: " << nbThresholdDoubt << std::endl;
               OSMWay & conflitWay = conflitDoc->addWay(batiWay, bati);
               
               conflitWay.importTags(*intersections[maxIndex].first, true);
               nbConflit++;
            }
         }
         else 
         {
            conflitDoc->addWay(batiWay, bati);
            nbConflit++;
         }
      }
   }
   
   std::cout << "Enregistrement fichiers de sortie..." << std::endl;
   okDoc->dumpOSM(outputPrefix+std::string(".ok.osm"));
   noFusionDoc->dumpOSM(outputPrefix+std::string(".nofusion.osm"));
   fusionDoc->dumpOSM(outputPrefix+std::string(".fusion.osm"));
   conflitDoc->dumpOSM(outputPrefix+std::string(".conflit.osm"));
   
   /*okDoc->dumpBoundingBoxes(outputPrefix+std::string(".ok.bounds.osm"));
   fusionDoc->dumpBoundingBoxes(outputPrefix+std::string(".fusion.bounds.osm"));
   conflitDoc->dumpBoundingBoxes(outputPrefix+std::string(".conflit.bounds.osm"));*/
   
   /*bati.dumpBoundingBoxes("boundsBati.osm");
   current.dumpBoundingBoxes("boundsCurrent.osm");*/
   
   delete okDoc;
   delete noFusionDoc;
   delete fusionDoc;
   delete conflitDoc;
   
   std::cout << "=======================================" << std::endl;
   std::cout << "Way OK:          " << nbOK << std::endl;
   std::cout << "Way sans fusion: " << nbNoFusion << std::endl;
   std::cout << "Way fusionnees:  " << nbFusion << std::endl;
   std::cout << "Way en conflit:  " << nbConflit << std::endl;
   std::cout << "=======================================" << std::endl;

}


