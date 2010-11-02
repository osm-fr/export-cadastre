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

void OSMGenerator::fillPath(const QPainterPath &path, const GraphicContext &context, Qt::FillRule fillRule)
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
        if (path.elementCount() != 5)
            qFatal("Invalid PDF bounding box found ?");
        m_pdfBoundingBox = path.boundingRect();
    } else {
        if (!m_colors.contains(context.brush.color())) {
            m_colors << context.brush.color();
            qDebug() << context.brush.color().name() << context.brush.color();
        }
    }
}

void OSMGenerator::strikePath(const QPainterPath &path, const GraphicContext &context)
{
    if ((context.pen.widthF() == 3.55) && (context.pen.style() == Qt::SolidLine)) {
        OSMPath result;
        result.path = path;
        result.tags["railway"] = "rail";
        m_rails << result;
    } else {
        if (!m_widths.contains(context.pen.widthF())) {
            qDebug() << context.pen.widthF();
            m_widths << context.pen.widthF();
        }
    }
}

void OSMGenerator::parsingDone(bool result)
{
    qDebug() << "I found " << m_houses.count() << " houses";
    qDebug() << "I found " << m_rails.count() << " rails";
    qDebug() << "I found " << m_waters.count() << " water";

    // TODO here : detect cemeteries, merge paths when they share points (or in dumpOSM when enumerating the points ?)...
}

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
    queries << QPair<QString, QList<OSMPath> *>(baseFileName + "-water.osm", &m_waters);
    queries << QPair<QString, QList<OSMPath> *>(baseFileName + "-rails.osm", &m_rails);
    queries << QPair<QString, QList<OSMPath> *>(baseFileName + "-houses.osm", &m_houses);

    OSMExecutor executor(this);
    QFuture<void> results = QtConcurrent::map(queries, executor);
    results.waitForFinished();
    /*dumpOSM(baseFileName + "-water.osm", &m_waters);
    dumpOSM(baseFileName + "-rails.osm", &m_rails);
    dumpOSM(baseFileName + "-houses.osm", &m_houses);*/
}

void OSMGenerator::dumpOSM(QPair<QString, QList<OSMPath> *> query) {
    return dumpOSM(query.first, query.second);
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
    qDebug() << boundsLatLon;
    writer.writeEmptyElement("bounds");
    writer.writeAttribute("minlat", QString::number(boundsLatLon[1].y(), 'f'));
    writer.writeAttribute("maxlat", QString::number(boundsLatLon[0].y(), 'f'));
    writer.writeAttribute("minlon", QString::number(boundsLatLon[0].x(), 'f'));
    writer.writeAttribute("maxlon", QString::number(boundsLatLon[1].x(), 'f'));

    QList<OSMPath> nPaths;

    // HOTSPOT : TO OPTIMIZE !
    foreach (OSMPath path, *paths) {
        QList<QPolygonF> sub_polygons = path.path.toSubpathPolygons();
        QList<int> sub_points;
        path.points_position.clear();
        if (sub_polygons.count() == 1) {
            foreach (QPointF pt, sub_polygons[0]) {
                int pos = nodes.indexOf(pt);
                if (pos == -1) {
                    pos = nodes.length();
                    nodes << pt;
                }
                sub_points << pos;
            }
            path.points_position << sub_points;
            nPaths << path;
        } else {
            qDebug() << "TODO : handle sub polygons in first pass !";
        }
    }
    // END HOT SPOT

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
    foreach (OSMPath path, nPaths) {
        if (path.points_position.count() == 1) {

            writer.writeStartElement("way");
            writer.writeAttribute("id", QString::number(-i));
            foreach (int pt, path.points_position[0]) {
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
            qDebug() << "TODO : handle sub polygons in second pass !" << path.points_position;
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
    result.reserve(points.count());
    for (int i = 0 ; i < points.count() ; i++) {
        result << QPointF(pointsX[i]*RAD_TO_DEG, pointsY[i]*RAD_TO_DEG);
    }
    delete(pointsX);
    delete(pointsY);
    return result;
}

