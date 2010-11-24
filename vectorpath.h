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

#ifndef VECTORPATH_H
#define VECTORPATH_H

#include <QPointF>
#include <QPainterPath>
#include <QPolygonF>
#include <QList>

/**
  This class is a bit like QPainterPath, but much simpler for our cases,
  which includes many polygon-only paths. This allows a more efficient implementation.
  In other cases, this class just map to a QPainterPath...
  */
class VectorPath
{
public:
    VectorPath();
    VectorPath(const VectorPath &other);
    VectorPath(const QPolygonF &polygon);
    void moveTo(qreal x, qreal y);
    void lineTo(qreal x, qreal y);
    void closeSubpath();
    QList<QPolygonF> toSubpathPolygons() const;
    void setFillRule(Qt::FillRule fillRule);
    QPainterPath toPainterPath() const;
    void quadTo(qreal cx, qreal cy, qreal endPointX, qreal endPointY);
    void cubicTo(qreal c1X, qreal c1Y, qreal c2X, qreal c2Y, qreal endPointX, qreal endPointY);
    bool isPainterPath() const;
    int pathCount() const;

    bool operator==(const VectorPath &other) const;
private:
    void convertToPainterPath();
    bool m_isPainterPath;
    QPainterPath m_painterPath;
    QList<QPolygonF> m_polygons;
    Qt::FillRule m_fillRule;
};

#endif // VECTORPATH_H
