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

#ifndef OSMGENERATOR_H
#define OSMGENERATOR_H

#include <QObject>
#include <QList>
#include <QPainterPath>
#include <QMap>
#include <QPointF>
#include "graphicproducer.h"

struct OSMPath {
    QPainterPath path;
    QMap<QString, QString> tags;
    QList<QList<int> > points_position;
};

class OSMGenerator : public QObject
{
    Q_OBJECT
public:
    explicit OSMGenerator(const QString &bbox, QObject *parent = 0);

    void dumpOSMs(const QString &baseFileName);

signals:

public slots:
    void strikePath(const QPainterPath &path, const GraphicContext &context);
    void fillPath(const QPainterPath &path, const GraphicContext &context, Qt::FillRule fillRule);
    void parsingDone(bool result);
    void dumpOSM(QPair<QString, QList<OSMPath> *> query);
private:
    void dumpOSM(const QString &fileName, QList<OSMPath> *paths);

    QList<QPointF> convertToEPSG4326(const QList<QPointF> points);

    QString m_projection;
    QRectF m_boundingBox, m_pdfBoundingBox;
    QPainterPath m_border;
    QList<OSMPath> m_houses;
    QList<OSMPath> m_waters;
    QList<OSMPath> m_rails;
    QList<QColor> m_colors;
    QList<qreal> m_widths;
};

#endif // OSMGENERATOR_H
