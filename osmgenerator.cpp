/* This file is part of Qadastre
 * Copyright (C) 2010 Pierre Ducroquet <pinaraf@pinaraf.info>
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public License
 * along with this library; see the file COPYING.LIB.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 * Boston, MA 02110-1301, USA.
 */

#include "osmgenerator.h"
#include <QDebug>
#include <QFile>
#include <QVariant>
#include <QRegExp>
#include <QStringList>
#include <QXmlStreamWriter>
#include <QDate>
#include <QCoreApplication>
#include <QSqlQuery>
#include <QSqlError>
#include <geos/geom/CoordinateSequenceFactory.h>
#include <geos/geom/GeometryFactory.h>
#include <geos/geom/PrecisionModel.h>
#include <geos/geom/MultiPolygon.h>
#include <geos/geom/LinearRing.h>
#include <geos/geom/Polygon.h>

bool OSMPath::operator ==(const OSMPath &other) const {
    return ((other.path == this->path) && (other.points_position == this->points_position) && (other.tags == this->tags));
}

OSMGenerator::OSMGenerator(const QString &bbox, const bool lands, QObject *parent) :
    QObject(parent),
    generateLands(lands)
{
    qDebug() << bbox;
    m_projection = bbox.split(":")[0];
    if (m_projection == "RGFG95UTM22")
    {
        m_projection = "UTM22RGFG95";
    }
    else if (m_projection == "RGR92UTM")
    {
        m_projection = "RGR92UTM40S";
    }

    char **argsSource = (char**) malloc(sizeof(char*));
    argsSource[0] = QString("init=IGNF:%1").arg(m_projection).toLocal8Bit().data();
    char **argsTarget = (char**) malloc(sizeof(char*));
    argsTarget[0] = (char *) "init=epsg:4326";

    if (!(m_projection_source = pj_init(1, argsSource)))
        qFatal(QString("Unable to initialize source projection %1").arg(m_projection).toLocal8Bit().data());

    if (!(m_projection_target = pj_init(1, argsTarget)))
        qFatal("Unable to initialize target projection");

    QStringList boundingBox = bbox.split(":")[1].split(",");
    m_boundingBox = QRectF(QPointF(boundingBox[0].toDouble(), boundingBox[3].toDouble()),
                           QPointF(boundingBox[2].toDouble(), boundingBox[1].toDouble()));
    qDebug() << "bb :" << m_boundingBox;
}

void OSMGenerator::fillPath(const VectorPath &path, const GraphicContext &context, Qt::FillRule fillRule)
{
    Q_UNUSED(fillRule);
    if (context.pen.widthF() > 30)
        qDebug() << "huge pen ?" << context.pen.widthF();
    if (context.brush.color() == QColor(255, 204, 51)) {
        OSMPath result;
        result.path = path;
        result.tags["building"] = "yes";
        m_houses << result;
    } else if (context.brush.color() == QColor(255, 229, 153)) {
        OSMPath result;
        result.path = path;
        result.tags["building"] = "yes";
        result.tags["wall"] = "no";
        m_houses << result;
    } else if (context.brush.color() == QColor::fromRgbF(0.596078, 0.764706, 0.85098)) {
        OSMPath result;
        result.path = path;
        result.tags["natural"] = "water";
        m_waters << result;
    } else if (context.brush.color() == QColor::fromRgbF(0.0980392, 0.47451, 0.67451)) {
        OSMPath result;
        result.path = path;
        result.tags["waterway"] = "riverbank";
        m_waters << result;
    } else if (context.brush.color() == Qt::white) {
        if (path.toPainterPath().elementCount() != 5) {
            qDebug() << "Invalid PDF bounding box found ?";
            //qFatal("Invalid PDF bounding box found ?");
        } else {
            m_pdfBoundingBox = path.toPainterPath().boundingRect();
        }
    } else {
        if (!m_colors.contains(context.brush.color())) {
            m_colors << context.brush.color();
            qDebug() << context.brush.color().name() << context.brush.color();
        }
    }
}

void OSMGenerator::strikePath(const VectorPath &path, const GraphicContext &context)
{
    if ((context.pen.widthF() == 17.86 || context.pen.widthF() == 8.5) && context.pen.style() == Qt::SolidLine) {
        // limit element...
        OSMPath result;
        result.path = path;
        result.tags["boundary"] = "administrative";
        m_cityLimit << result;
    } else if (generateLands && context.pen.widthF() == 0.76063 && context.pen.style() == Qt::SolidLine) {
        // Ensure poly closed
        QList<QPolygonF> polygons = path.toSubpathPolygons();
        bool poly = false;
        foreach (const QPolygonF &polygon, polygons) {
          poly = poly || polygon.isClosed();
        }
        if (poly) {
          OSMPath result;
          result.path = path;
          m_lands << result;
        }
    } else if ((context.pen.widthF() == 3.55) && (context.pen.style() == Qt::SolidLine)) {
        qDebug() << "Candidate for future church ?";
        //qDebug() << path.pathCount() << path.toSubpathPolygons();
        if (!path.isPainterPath()) {
            if (path.pathCount() == 1) {
                QPolygonF firstPolygon = path.toSubpathPolygons()[0];
                if (firstPolygon.count() == 2) {
                    m_railLines << QLineF(firstPolygon.first(), firstPolygon.last());
                    qDebug() << "Potential cross ?" << m_railLines.last();
                }
            } else if (path.pathCount() == 2) {
                QList<QPolygonF> polygons = path.toSubpathPolygons();
                if ((polygons[0].count() <= 4) && (polygons[1].count() <= 4)) {
                    QPointF church;
                    if (QLineF(polygons[0].first(), polygons[0].last()).intersect(QLineF(polygons[1].first(), polygons[1].last()), &church)) {
                        m_churches << church;
                        return;
                    }
                }
            }
        }

        OSMPath result;
        result.path = path;
        result.tags["railway"] = "rail";
        m_rails << result;
    } else if ((!path.isPainterPath()) && (path.pathCount() == 1) && (context.pen.color() == Qt::black) && (context.pen.style() == Qt::SolidLine)) {
        QPolygonF polygon = path.toSubpathPolygons()[0];
        if (polygon.count() == 2) {
            QLineF line(polygon[0], polygon[1]);
            if ((context.clipPath.contains(line.p1())) && (context.clipPath.contains(line.p2()))) {
                // This is a candidate for a cemetery !
                if (line.dy() == 0) {
                    m_hLines << line;
                } else if (line.dx() == 0) {
                    // This is a vLine, check it against hLines first
                    bool found = false;
                    foreach (const QLineF &hLine, m_hLines) {
                        QPointF cross;
                        if (hLine.intersect(line, &cross)) {
                            if ((cross.x() - hLine.x1()) == (hLine.x2() - cross.x())) {
                                if ((cross.y() - line.y1()) != (line.y2() - cross.y())) {
                                    m_crosses.append(cross);
                                    m_hLines.removeOne(hLine);
                                    found = true;
                                    break;
                                }
                            }
                        }
                    }
                    if (!found)
                        m_vLines << line;
                }
            }
        }
    }
    if (context.pen.style() == Qt::SolidLine) {
        if (context.pen.color() == Qt::black) {
            QPolygonF polyPath = path.toSubpathPolygons()[0];
            if (polyPath.isClosed())
                m_closedPolygons.append(polyPath);
        }
    }
}

bool polygonLess(const QPolygonF &p1, const QPolygonF &p2) {
    if (p1.size() != p2.size()) {
         return p1.size() < p2.size();
    } else if (p1 == p2) {
        return false;
    } else {
        return &p1 < &p2;
    }
}

void OSMGenerator::parsingDone(bool result)
{
    if (!result)
    {
        qFatal("Parsing failed");
        return;
    }
    qDebug() << "I found " << m_houses.count() << " houses";
    qDebug() << "I found " << m_rails.count() << " rails";
    qDebug() << "I found " << m_waters.count() << " water";
    if (generateLands) {
      qDebug() << "I found " << m_lands.count() << " land";
    }

    // TODO here : merge paths when they share points (or in dumpOSM when enumerating the points ?)...
    // Detect cemeteries
    qDebug() << "Number of possible cross lines : " << m_vLines.count() << m_hLines.count();
    foreach (const QLineF &hLine, m_hLines) {
        foreach (const QLineF &vLine, m_vLines) {
            QPointF cross;
            if (hLine.intersect(vLine, &cross)) {
                if ((cross.x() - hLine.x1()) == (hLine.x2() - cross.x())) {
                    if ((cross.y() - vLine.y1()) != (vLine.y2() - cross.y())) {
                        m_crosses.append(cross);
                    }
                }
                m_vLines.removeAll(vLine);
                break;
            }
        }
        m_hLines.removeAll(hLine);
    }
    qDebug() << "I found " << m_crosses.count() << " crosses.";
    qDebug() << "Gonna check against " << m_closedPolygons.count() << " elements.";
    QPainterPath candidateCemeteries;
    foreach(const QPolygonF &polygon, m_closedPolygons) {
        int countCrosses = 0;
        foreach(const QPointF &cross, m_crosses) {
            if ((polygon.containsPoint(cross, Qt::OddEvenFill)) || (polygon.containsPoint(cross, Qt::WindingFill))) {
                countCrosses++;
                m_crosses.removeOne(cross);
            }
        }

        if (countCrosses > 5) {
            qDebug() << "Cemetery area with " << countCrosses << " crosses";
            candidateCemeteries.addPolygon(polygon);
        }
    }
    qDebug() << "Now I've got " << candidateCemeteries.elementCount() << " candidates.";

    QList<QPolygonF> cemeteries_final = candidateCemeteries.simplified().toSubpathPolygons();
    foreach(const QPolygonF &cemetery, cemeteries_final) {
        OSMPath result;
        result.path = VectorPath(cemetery);
        result.tags["landuse"] = "cemetery";
        m_cemeteries << result;
    }

    // Detect churchs
    foreach (const QLineF &railLine, m_railLines) {
        qDebug() << railLine;
        QList<QLineF> intersecting;
        QList<QPointF> crosses;
        foreach (const QLineF &railLine2, m_railLines) {
            qDebug() << railLine2;
            if (railLine2 == railLine)
                continue;
            if ((railLine.p1() == railLine2.p1()) || (railLine.p1() == railLine2.p2())) {
                intersecting << railLine2;
                if (!crosses.contains(railLine.p1()))
                    crosses << railLine.p1();
            }
            if ((railLine.p2() == railLine2.p1()) || (railLine.p2() == railLine2.p2())) {
                intersecting << railLine2;
                if (!crosses.contains(railLine.p2()))
                    crosses << railLine.p2();
            }
        }

        if ((intersecting.length() == 3) && (crosses.count() == 1)) {
            if (!m_churches.contains(crosses.first()))
                m_churches << crosses.first();
        }
    }
    if (!m_churches.isEmpty()) {
        qDebug() << "I've got a church, find the useless rails now !";
        int idx = 0;
        foreach (const OSMPath &railPath, m_rails) {
            if ((!railPath.path.isPainterPath()) && (railPath.path.pathCount() == 1)) {
                QPolygonF polygon = railPath.path.toSubpathPolygons().first();
                if (polygon.count() == 2) {
                    if ((m_churches.contains(polygon.first())) || (m_churches.contains(polygon.last()))) {
                        m_rails.removeAt(idx);
                        continue;
                    }
                }
            }
            idx++;
        }

        QList<OSMPath>::iterator itHouse;
        for (itHouse = m_houses.begin() ; itHouse != m_houses.end() ; ++itHouse) {
            if (!(*itHouse).path.isPainterPath()) {
                QPolygonF poly = (*itHouse).path.toSubpathPolygons().first();
                bool found = false;
                foreach (const QPointF &church, m_churches) {
                    if (poly.containsPoint(church, Qt::WindingFill)) {
                        (*itHouse).tags.insert("amenity", "place_of_worship");
                        (*itHouse).tags.insert("denomination", "catholic");
                        (*itHouse).tags.insert("religion", "christian");
                        m_churches.removeOne(church);
                        found = true;
                    }
                }
                if (found)
                    if (m_churches.count() == 0)
                        break;
            }
        }
    }
    qDebug() << "Churches found :" << m_churches;

    if (!m_cityLimit.empty()) {
        VectorPath resultCityLimit;

        qDebug() << "Now detect inners and outers city limits";

        // Disassemble OSMPath
        QList<QPolygonF> polygons0;
        foreach(const OSMPath &osmPath, m_cityLimit) {
            polygons0 << osmPath.path.toSubpathPolygons();
        }

        // Clean input, only one instance of each polygon
        qSort(polygons0.begin(), polygons0.end(), polygonLess);
        QList<QPolygonF> polygons;
        for(QList<QPolygonF>::iterator ip = polygons0.begin(); ip != polygons0.end() ; ++ip) {
            if(ip->size() > 0 && (polygons.empty() || polygons.back() != *ip)) {
                polygons << *ip;
            }
        }

        // Detect inner and outer
        // Let say polygons never intersect other polygons
        for(QList<QPolygonF>::iterator ip1 = polygons.begin(); ip1 != polygons.end() ; ++ip1) {
            bool is_inner = false;
            for(QList<QPolygonF>::iterator ip2 = polygons.begin(); ip2 != polygons.end() ; ++ip2) {
                if(*ip1 != *ip2) {
                    foreach(const QPointF &point1, *ip1) {
                        if(ip2->containsPoint(point1, Qt::WindingFill)) {
                            // polygon1 is inside polygon2
                            is_inner = true;
                            break;
                        }
                    }
                    if(is_inner) {
                        break;
                    }
                }
            }
            // Reassemble polygons on OSMPath
            resultCityLimit.addSubpath(*ip1, is_inner);
        }

       // Replace initial city limit
       m_cityLimit.clear();
       OSMPath result;
       result.path = resultCityLimit;
       result.tags["boundary"] = "administrative";
       m_cityLimit << result;
    }
}

void OSMGenerator::dumpOSMs(const QString &baseFileName)
{
    qDebug() << "Going to dump osms";
    // Once proj 4.8 is available, one thread should be used for each category here
    if (!m_waters.isEmpty())
        dumpOSM(baseFileName + "-water.osm", &m_waters, true);
    if (!m_rails.isEmpty())
        dumpOSM(baseFileName + "-rails.osm", &m_rails);
    if (!m_houses.isEmpty())
        dumpOSM(baseFileName + "-houses.osm", &m_houses);
    if (!m_cemeteries.isEmpty())
        dumpOSM(baseFileName + "-cemeteries.osm", &m_cemeteries);
    if (!m_cityLimit.isEmpty())
        dumpOSM(baseFileName + "-city-limit.osm", &m_cityLimit);
    if (generateLands && !m_lands.isEmpty())
        dumpOSM(baseFileName + "-lands.osm", &m_lands);
}

#define areaCodeFromPt(pt) ((int(pt.x()/(m_pdfBoundingBox.width()/1000)) * 1000) + int(pt.y()/(m_pdfBoundingBox.height()/1000)))

void OSMGenerator::dumpOSM(const QString &fileName, QList<OSMPath> *paths, bool merge)
{
    qDebug() << "Dumping to " << fileName << " ==> " << paths->size() << "elements";
    if (merge) {
        qDebug() << "Merging...";
        QList<OSMPath> new_paths;
        QList<QRectF> bounding_boxes;
        foreach (const OSMPath &path, *paths) {
            QRectF bounding_box = path.path.boundingRect();
            bool found = false;
            int i = 0;
            foreach (const QRectF &bounding, bounding_boxes) {
                if (bounding.intersects(bounding_box)) {
                    if ((new_paths[i].path.toPainterPath().intersects(path.path.toPainterPath())) && (new_paths[i].tags == path.tags)) {
                        new_paths[i].path = VectorPath(new_paths[i].path.toPainterPath().united(path.path.toPainterPath()));
                        bounding_boxes[i] = bounding.united(bounding_box);
                        found = true;
                        break;
                    }
                }
                i++;
            }
            if (!found) {
                new_paths.append(path);
                bounding_boxes.append(bounding_box);
            }
        }
        *paths = new_paths;
        qDebug() << "Merge done";
    }

    QList<QPointF> nodes;

    QString source = QString::fromUtf8("cadastre-dgi-fr source : Direction Générale des Finances Publiques - Cadastre. Mise à jour : %1").arg(QDate::currentDate().year());

    QFile target(fileName);
    if (!target.open(QIODevice::WriteOnly)) {
        qFatal("Unable to open the file for writing");
    }
    QXmlStreamWriter writer(&target);
    writer.setAutoFormatting(true);
    writer.writeStartDocument();

    writer.writeStartElement("osm");
    writer.writeAttribute("version", "0.6");
    writer.writeAttribute("generator", "Qadastre");

    QList<QPointF> boundsLatLon = convertToEPSG4326(QList<QPointF>() << m_pdfBoundingBox.topLeft() << m_pdfBoundingBox.bottomRight());
    writer.writeEmptyElement("bounds");
    writer.writeAttribute("minlat", QString::number(boundsLatLon[1].y(), 'f'));
    writer.writeAttribute("maxlat", QString::number(boundsLatLon[0].y(), 'f'));
    writer.writeAttribute("minlon", QString::number(boundsLatLon[0].x(), 'f'));
    writer.writeAttribute("maxlon", QString::number(boundsLatLon[1].x(), 'f'));

    QList<OSMPath> goodPaths;
    qDebug() << "Extracting nodes...";

    typedef QPair<QPointF, int> PointPositionned;
    QHash<int, QList<PointPositionned> > hashedPoints;
    foreach (OSMPath path, *paths) {
        QList<QPolygonF> sub_polygons = path.path.toSubpathPolygons();
        path.points_position.clear();
        foreach (const QPolygonF &sub_polygon, sub_polygons) {
            if (sub_polygon.isEmpty())
                continue;
            QList<int> sub_points;
            foreach (const QPointF &pt, sub_polygon) {
                int area = areaCodeFromPt(pt);
                int pos = -1;
                if (hashedPoints.contains(area)) {
                    //const QPair<QPointF, int> &areaPoint;
                    const QList<PointPositionned> &areaPoints = hashedPoints[area];
                    foreach (const PointPositionned &areaPoint, areaPoints) {
                        if (areaPoint.first == pt) {
                            pos = areaPoint.second;
                            break;
                        }
                    }
                } else {
                    hashedPoints[area] = QList<PointPositionned >();
                }
                if (pos == -1) {
                    pos = nodes.size();
                    nodes << pt;
                    hashedPoints[area].append(QPair<QPointF, int>(pt, pos));
                }
                sub_points << pos;
            }
            path.points_position << sub_points;
        }
        if (path.points_position.size() > 0)
            goodPaths << path;
    }

    qDebug()  << "Done extracting nodes";

    QList<QPointF> tNodes = convertToEPSG4326(nodes);

    int i = 1;
    foreach (const QPointF &node, tNodes) {
        writer.writeEmptyElement("node");
        writer.writeAttribute("id", QString::number(-i));
        writer.writeAttribute("lat", QString::number(node.y(), 'f'));
        writer.writeAttribute("lon", QString::number(node.x(), 'f'));
        i++;
    }

    i = 1;
    foreach (const OSMPath &path, goodPaths) {
        if (path.points_position.count() == 1) {
            writer.writeStartElement("way");
            writer.writeAttribute("id", QString::number(-i));
            foreach (int pt, path.points_position.first()) {
                writer.writeEmptyElement("nd");
                writer.writeAttribute("ref", QString::number(-pt - 1));
            }

            writer.writeEmptyElement("tag");
            writer.writeAttribute("k", "source");
            writer.writeAttribute("v", source);

            QMap<QString, QString>::const_iterator tags = path.tags.constBegin();
            while (tags != path.tags.constEnd()) {
                writer.writeEmptyElement("tag");
                writer.writeAttribute("k", tags.key());
                writer.writeAttribute("v", tags.value());
                ++tags;
            }
            writer.writeEndElement();
            i++;
        } else {
            qDebug() << "We have a multipolygon" << path.points_position.count();
            
            // Let's say the outer polygon is always the first one
            int nOuter = path.path.getNOuter();
            QList<int> wayNumbers;
            foreach (const QList<int> &nodesPositions, path.points_position) {
                writer.writeStartElement("way");
                writer.writeAttribute("id", QString::number(-i));
                wayNumbers << -i;
                foreach (int pt, nodesPositions) {
                    writer.writeEmptyElement("nd");
                    writer.writeAttribute("ref", QString::number(-pt - 1));
                }

                writer.writeEmptyElement("tag");
                writer.writeAttribute("k", "source");
                writer.writeAttribute("v", source);

                if (nOuter > 0) {
                    QMap<QString, QString>::const_iterator tags = path.tags.constBegin();
                    while (tags != path.tags.constEnd()) {
                        writer.writeEmptyElement("tag");
                        writer.writeAttribute("k", tags.key());
                        writer.writeAttribute("v", tags.value());
                        ++tags;
                    }
                    nOuter--;
                }
                writer.writeEndElement();
                i++;
            }

            writer.writeStartElement("relation");
            writer.writeAttribute("id", QString::number(-i));

            writer.writeEmptyElement("tag");
            writer.writeAttribute("k", "type");
            writer.writeAttribute("v", "multipolygon");

            nOuter = path.path.getNOuter();
            foreach(int wayId, wayNumbers) {
                writer.writeEmptyElement("member");
                writer.writeAttribute("type", "way");
                writer.writeAttribute("ref", QString::number(wayId));
                if (nOuter > 0) {
                    writer.writeAttribute("role", "outer");
                    nOuter--;
                } else {
                    writer.writeAttribute("role", "inner");
                }
            }

            writer.writeEndElement();
            i++;
        }
    }

    writer.writeEndElement(); // osm

    writer.writeEndDocument();
}

void OSMGenerator::dumpSQLs(const QSqlDatabase &db, int cityId, int importId)
{
    qDebug() << "dump sqls !";
    if (!m_waters.isEmpty())
        dumpSQL(db, cityId, importId, "water", &m_waters, true);
/*    if (!m_rails.isEmpty())
        dumpSQL(db, cityId, importId, "rail", &m_rails);*/
    if (!m_houses.isEmpty())
        dumpSQL(db, cityId, importId, "house", &m_houses);
    if (!m_cemeteries.isEmpty())
        dumpSQL(db, cityId, importId, "cemetery", &m_cemeteries);
    if (!m_cityLimit.isEmpty())
        dumpSQL(db, cityId, importId, "city-limit", &m_cityLimit);
}

void OSMGenerator::dumpSQL(const QSqlDatabase &db, int cityId, int importId, const QString &type, QList<OSMPath> *paths, bool merge)
{
    QString realType = type;
    if (merge) {
        QList<OSMPath> new_paths;
        QList<QRectF> bounding_boxes;
        foreach (const OSMPath &path, *paths) {
            QRectF bounding_box = path.path.boundingRect();
            bool found = false;
            int i = 0;
            foreach (const QRectF &bounding, bounding_boxes) {
                if (bounding.intersects(bounding_box)) {
                    if ((new_paths[i].path.toPainterPath().intersects(path.path.toPainterPath())) && (new_paths[i].tags == path.tags)) {
                        new_paths[i].path = VectorPath(new_paths[i].path.toPainterPath().united(path.path.toPainterPath()));
                        bounding_boxes[i] = bounding.united(bounding_box);
                        found = true;
                        break;
                    }
                }
                i++;
            }
            if (!found) {
                new_paths.append(path);
                bounding_boxes.append(bounding_box);
            }
        }
        *paths = new_paths;
    }

    geos::geom::PrecisionModel precision;
    geos::geom::GeometryFactory factory(&precision, 4326);

    qDebug() << "Done extracting nodes";

    QList<int> polygonIds;

    foreach (const OSMPath &path, *paths) {
        if ((path.tags.contains("amenity")) && (path.tags["amenity"] == "place_of_worship"))
            realType = "church";
        QList<QPolygonF> sub_polygons = path.path.toSubpathPolygons();

        std::vector<geos::geom::Geometry*> geoPolygons;

        foreach (const QPolygonF qPoly, sub_polygons) {
            if (qPoly.isEmpty())
                continue;
            if (!qPoly.isClosed())
            {
                qDebug() << "hara-kiri : " << type << realType << qPoly;
                qFatal("Banzai");
            }
            QList<QPointF> pts = convertToEPSG4326(qPoly.toList());
            if (pts.size() > 3) {
                qDebug() << "Working on the points";
                std::vector<geos::geom::Coordinate> *coords = new std::vector<geos::geom::Coordinate>;
                foreach (const QPointF pt, pts)
                {
                    coords->push_back(geos::geom::Coordinate(pt.x(), pt.y()));
                }
                geos::geom::CoordinateSequence *seq = factory.getCoordinateSequenceFactory()->create(coords);
                geos::geom::LinearRing *ring = factory.createLinearRing(seq);
                geos::geom::Polygon *poly = factory.createPolygon(ring, 0);
                geoPolygons.push_back(poly);
            } else if (pts.size() > 0) {
                qDebug() << "Really weird !!!";
                qDebug() << type << realType << pts;
            }
        }

        if (geoPolygons.size()) {
            geos::geom::MultiPolygon *mPoly = factory.createMultiPolygon(geoPolygons);
            QString wkt = QString::fromStdString(mPoly->toString());

            int houseId;
            qDebug() << "Created a multi-polygon to check";
            QSqlQuery qry(db);
            qry.prepare("SELECT id FROM houses WHERE \"type\"=:t AND city=:c AND geom=setsrid(st_geomfromewkt(:g), 4326) AND substring(geom::bytea for 2048) = substring(setsrid(st_geomfromewkt(:g2), 4326)::bytea for 2048)");
            qry.bindValue(":t", realType);
            qry.bindValue(":c", cityId);
            qry.bindValue(":g", wkt);
            qry.bindValue(":g2", wkt);

            if (!qry.exec()) {
                qDebug() << "In selection :";
                qFatal(qry.lastError().text().toLocal8Bit());
                qApp->exit(-2);
                return;
            }

            if (qry.next()) {
                houseId = qry.value(0).toInt();
            } else {
                // Insert the polygon now
                qDebug() << "Inserting ?";
                QSqlQuery insertQry(db);
                insertQry.prepare("INSERT INTO houses(city, \"type\", geom) VALUES (:c, :t, setsrid(st_geomfromewkt(:g)::geometry, 4326)) RETURNING id");
                insertQry.bindValue(":t", realType);
                insertQry.bindValue(":c", cityId);
                insertQry.bindValue(":g", wkt);

                if (!insertQry.exec()) {
                    qDebug() << "In polygon insertion :";
                    qFatal(insertQry.lastError().text().toLocal8Bit());
                    qApp->exit(-2);
                    return;
                }

                if (insertQry.next()) {
                    houseId = insertQry.value(0).toInt();
                }
            }

            if (polygonIds.contains(houseId)) {
                qWarning("Duplicate polygon");
            } else {
                polygonIds << houseId;
            }
        } else {
            // Nothing so far
        }
    }

    qDebug() << "Done inserting all polygons !";
    // Insert all there polygonIds
    QSqlQuery insertImportHouse(db);
    insertImportHouse.prepare("INSERT INTO import_houses (import, house) VALUES (:i, :h)");
    foreach (int polygonId, polygonIds)
    {
        insertImportHouse.bindValue(":h", polygonId);
        insertImportHouse.bindValue(":i", importId);
        if (!insertImportHouse.exec()) {
            qDebug() << "In import_house insertion :";
            qFatal(insertImportHouse.lastError().text().toLocal8Bit());
        }
    }
}

QList<QPointF> OSMGenerator::convertToEPSG4326(const QList<QPointF> &points)
{
    double *pointsX = new double[points.count()];
    double *pointsY = new double[points.count()];

    for (int i = 0 ; i < points.count() ; i++) {
        pointsX[i] = m_boundingBox.left() + m_boundingBox.width() * points[i].x() / m_pdfBoundingBox.width();
        pointsY[i] = m_boundingBox.top() - m_boundingBox.height() * (points[i].y() / m_pdfBoundingBox.height() - 1);
    }

    int transform = pj_transform(m_projection_source, m_projection_target, points.count(), 1, pointsX, pointsY, 0);
    if (transform != 0)
        qFatal("Error while transforming");

    QList<QPointF> result;
    #if QT_VERSION >= 0x040700
    // Reserve is an optimization available only with Qt 4.7...
    result.reserve(points.count());
    #endif
    for (int i = 0 ; i < points.count() ; i++) {
        result << QPointF(pointsX[i]*RAD_TO_DEG, pointsY[i]*RAD_TO_DEG);
    }
    delete(pointsX);
    delete(pointsY);
    return result;
}
