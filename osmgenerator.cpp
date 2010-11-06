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
#include <QRegExp>
#include <QStringList>
#include <QXmlStreamWriter>
#include <QDate>
#include <QtConcurrentMap>
#include <QCoreApplication>
#include <proj_api.h>

OSMGenerator::OSMGenerator(const QString &bbox, QObject *parent) :
    QObject(parent)
{
    qDebug() << bbox;
    m_projection = bbox.split(":")[0];
    QStringList boundingBox = bbox.split(":")[1].split(",");
    m_boundingBox = QRectF(QPointF(boundingBox[0].toDouble(), boundingBox[3].toDouble()),
                           QPointF(boundingBox[2].toDouble(), boundingBox[1].toDouble()));
}

void OSMGenerator::fillPath(const VectorPath &path, const GraphicContext &context, Qt::FillRule fillRule)
{
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
        if (path.toPainterPath().elementCount() != 5)
            qFatal("Invalid PDF bounding box found ?");
        m_pdfBoundingBox = path.toPainterPath().boundingRect();
    } else {
        if (!m_colors.contains(context.brush.color())) {
            m_colors << context.brush.color();
            qDebug() << context.brush.color().name() << context.brush.color();
        }
    }
}

void OSMGenerator::strikePath(const VectorPath &path, const GraphicContext &context)
{
    if ((context.pen.widthF() == 3.55) && (context.pen.style() == Qt::SolidLine)) {
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
                    foreach (QLineF hLine, m_hLines) {
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

void OSMGenerator::parsingDone(bool result)
{
    qDebug() << "I found " << m_houses.count() << " houses";
    qDebug() << "I found " << m_rails.count() << " rails";
    qDebug() << "I found " << m_waters.count() << " water";

    // TODO here : merge paths when they share points (or in dumpOSM when enumerating the points ?)...
    // Detect cemeteries
    qDebug() << "Number of possible cross lines : " << m_vLines.count() << m_hLines.count();
    foreach (QLineF hLine, m_hLines) {
        foreach (QLineF vLine, m_vLines) {
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
    foreach(QPolygonF polygon, m_closedPolygons) {
        int countCrosses = 0;
        foreach(QPointF cross, m_crosses) {
            if ((polygon.containsPoint(cross, Qt::OddEvenFill)) || (polygon.containsPoint(cross, Qt::WindingFill))) {
                countCrosses++;
                m_crosses.removeOne(cross);
            }
        }

        if (countCrosses > 5) {
            qDebug() << countCrosses << polygon;
            candidateCemeteries.addPolygon(polygon);
        }
    }
    qDebug() << "Now I've got " << candidateCemeteries.elementCount() << " candidates.";

    QList<QPolygonF> cemeteries_final = candidateCemeteries.simplified().toSubpathPolygons();
    foreach(QPolygonF cemetery, cemeteries_final) {
        OSMPath result;
        result.path = VectorPath(cemetery);
        result.tags["landuse"] = "cemetery";
        m_cemeteries << result;
    }
}

#if 0
/*
Multi thread is not possible with proj4, this is dangerous.
We would need proj4 4.8, and it is not releaused yet (november 2010)
*/
struct OSMExecutor
{
    OSMExecutor(OSMGenerator *osmGenerator)
    : m_osmGenerator(osmGenerator) { }

    typedef void result_type;

    void operator()(QPair<QString, QList<OSMPath> *> query)
    {
        return m_osmGenerator->dumpOSM(query);
    }

    OSMGenerator *m_osmGenerator;
};

void OSMGenerator::dumpOSMs(const QString &baseFileName)
{
    QList<QPair<QString, QList<OSMPath> *> > queries;
    if (!m_waters.isEmpty())
        queries << QPair<QString, QList<OSMPath> *>(baseFileName + "-water.osm", &m_waters);
    if (!m_rails.isEmpty())
        queries << QPair<QString, QList<OSMPath> *>(baseFileName + "-rails.osm", &m_rails);
    if (!m_houses.isEmpty())
        queries << QPair<QString, QList<OSMPath> *>(baseFileName + "-houses.osm", &m_houses);
    if (!m_cemeteries.isEmpty())
        queries << QPair<QString, QList<OSMPath> *>(baseFileName + "-cemeteries.osm", &m_cemeteries);

    OSMExecutor executor(this);
    QFuture<void> results = QtConcurrent::map(queries, executor);
    results.waitForFinished();
}

void OSMGenerator::dumpOSM(QPair<QString, QList<OSMPath> *> query) {
    return dumpOSM(query.first, query.second);
}
#endif

void OSMGenerator::dumpOSMs(const QString &baseFileName)
{
    if (!m_waters.isEmpty())
        dumpOSM(baseFileName + "-water.osm", &m_waters);
    if (!m_rails.isEmpty())
        dumpOSM(baseFileName + "-rails.osm", &m_rails);
    if (!m_houses.isEmpty())
        dumpOSM(baseFileName + "-houses.osm", &m_houses);
    if (!m_cemeteries.isEmpty())
        dumpOSM(baseFileName + "-cemeteries.osm", &m_cemeteries);
}

void OSMGenerator::dumpOSM(const QString &fileName, QList<OSMPath> *paths)
{
    QList<QPointF> nodes;

    QString source = QString::fromUtf8("cadastre-dgi-fr source : Direction Générale des Impôts - Cadastre. Mise à jour : %1").arg(QDate::currentDate().year());

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
    foreach (OSMPath path, *paths) {
        QList<QPolygonF> sub_polygons = path.path.toSubpathPolygons();
        path.points_position.clear();
        foreach (QPolygonF sub_polygon, sub_polygons) {
            if (sub_polygon.isEmpty())
                continue;
            QList<int> sub_points;
            foreach (QPointF pt, sub_polygon) {
                int pos = nodes.indexOf(pt);
                if (pos == -1) {
                    pos = nodes.length();
                    nodes << pt;
                }
                sub_points << pos;
            }
            path.points_position << sub_points;
            goodPaths << path;
        }
    }

    qDebug()  << "Done extracting nodes";

    QList<QPointF> tNodes = convertToEPSG4326(nodes);

    int i = 1;
    foreach (QPointF node, tNodes) {
        writer.writeStartElement("node");
        writer.writeAttribute("id", QString::number(-i));
        writer.writeAttribute("lat", QString::number(node.y(), 'f'));
        writer.writeAttribute("lon", QString::number(node.x(), 'f'));
        writer.writeEmptyElement("tag");
        writer.writeAttribute("k", "source");
        writer.writeAttribute("v", source);
        writer.writeEndElement();
        i++;
    }

    i = 1;
    foreach (OSMPath path, goodPaths) {
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

            writer.writeEmptyElement("tag");
            writer.writeAttribute("k", "note:qadastre");
            writer.writeAttribute("v", "v0.1");

            writer.writeEndElement();
            i++;
        } else {
            qDebug() << "We have a multipolygon" << path.points_position.count();
            // Let's say the outer polygon is always the first one
            bool isOuter = true;
            QList<int> wayNumbers;
            foreach (QList<int> nodesPositions, path.points_position) {
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

                if (isOuter) {
                    QMap<QString, QString>::const_iterator tags = path.tags.constBegin();
                    while (tags != path.tags.constEnd()) {
                        writer.writeEmptyElement("tag");
                        writer.writeAttribute("k", tags.key());
                        writer.writeAttribute("v", tags.value());
                        ++tags;
                    }
                    isOuter = false;
                }

                writer.writeEmptyElement("tag");
                writer.writeAttribute("k", "note:qadastre");
                writer.writeAttribute("v", "v0.1");

                writer.writeEndElement();
                i++;
            }

            writer.writeStartElement("relation");
            writer.writeAttribute("id", QString::number(-i));

            writer.writeEmptyElement("tag");
            writer.writeAttribute("k", "type");
            writer.writeAttribute("v", "multipolygon");

            isOuter = true;
            foreach(int wayId, wayNumbers) {
                writer.writeEmptyElement("member");
                writer.writeAttribute("type", "way");
                writer.writeAttribute("ref", QString::number(wayId));
                if (isOuter) {
                    writer.writeAttribute("role", "outer");
                    isOuter = false;
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

QList<QPointF> OSMGenerator::convertToEPSG4326(const QList<QPointF> points)
{
    double *pointsX = new double[points.count()];
    double *pointsY = new double[points.count()];

    for (int i = 0 ; i < points.count() ; i++) {
        pointsX[i] = m_boundingBox.left() + m_boundingBox.width() * points[i].x() / m_pdfBoundingBox.width();
        pointsY[i] = m_boundingBox.top() - m_boundingBox.height() * (points[i].y() / m_pdfBoundingBox.height() - 1);
    }

    char *argsSource[] = { QString("init=IGNF:%1").arg(m_projection).toLocal8Bit().data() };
    char *argsTarget[] = { "init=epsg:4326" };
    projPJ source;
    projPJ target;

    if (!(source = pj_init(1, argsSource)))
        qFatal("Unable to initialize source projection");

    if (!(target = pj_init(1, argsTarget)))
        qFatal("Unable to initialize target projection");

    int transform = pj_transform(source, target, points.count(), 1, pointsX, pointsY, 0);
    if (transform != 0)
        qFatal("Error while trasforming");

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

