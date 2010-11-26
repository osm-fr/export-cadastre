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

#include "vectorpath.h"

VectorPath::VectorPath()
    : m_isPainterPath(false)
{
}

VectorPath::VectorPath(const QPainterPath &painterPath)
{
    m_isPainterPath = true;
    m_painterPath = painterPath;
    m_fillRule = painterPath.fillRule();
}

VectorPath::VectorPath(const VectorPath &other)
{
    m_isPainterPath = other.m_isPainterPath;
    m_painterPath = other.m_painterPath;
    m_polygons = other.m_polygons;
    m_fillRule = other.m_fillRule;
}

VectorPath::VectorPath(const QPolygonF &polygon)
    : m_isPainterPath(false)
{
    m_polygons << polygon;
}

bool VectorPath::operator ==(const VectorPath &other) const {
    return (m_isPainterPath == other.m_isPainterPath) && (m_polygons == other.m_polygons) && (m_painterPath == other.m_painterPath);
}

void VectorPath::lineTo(qreal x, qreal y)
{
    if (m_isPainterPath) {
        m_painterPath.lineTo(x, y);
    } else {
        if (m_polygons.empty())
            m_polygons << QPolygonF();
        m_polygons.last().append(QPointF(x, y));
    }
}

void VectorPath::moveTo(qreal x, qreal y)
{
    if (m_isPainterPath) {
        m_painterPath.moveTo(x, y);
    } else {
        if ((m_polygons.empty()) || (!m_polygons.last().empty()))
            m_polygons << QPolygonF();
        m_polygons.last().append(QPointF(x, y));
    }
}

QList<QPolygonF> VectorPath::toSubpathPolygons() const
{
    if (m_isPainterPath)
        return m_painterPath.toSubpathPolygons();
    else
        return m_polygons;
}

void VectorPath::closeSubpath()
{
    if (m_isPainterPath) {
        m_painterPath.closeSubpath();
    } else {
        if (m_polygons.last().count() > 0) {
            if (!m_polygons.last().isClosed())
                m_polygons.last() << m_polygons.last().first();
        }
        m_polygons << QPolygonF();  // Is that needed ?
    }
}

void VectorPath::setFillRule(Qt::FillRule fillRule)
{
    m_painterPath.setFillRule(fillRule);
}

void VectorPath::quadTo(qreal cx, qreal cy, qreal endPointX, qreal endPointY)
{
    if (!m_isPainterPath)
        convertToPainterPath();
    m_painterPath.quadTo(cx, cy, endPointX, endPointY);
}

void VectorPath::cubicTo(qreal c1X, qreal c1Y, qreal c2X, qreal c2Y, qreal endPointX, qreal endPointY)
{
    if (!m_isPainterPath)
        convertToPainterPath();
    m_painterPath.cubicTo(c1X, c1Y, c2X, c2Y, endPointX, endPointY);
}

QPainterPath VectorPath::toPainterPath() const
{
    if (m_isPainterPath)
        return m_painterPath;
    // Build the painter path then...
    QPainterPath result;
    bool firstPath = true;
    foreach (QPolygonF polygon, m_polygons) {
        if (!firstPath)
            result.closeSubpath();
        firstPath = false;
        if (!polygon.isEmpty()) {
            result.moveTo(polygon.first());
            bool first = true;
            foreach (QPointF point, polygon) {
                if (first)
                    first = false;
                else
                    result.lineTo(point);
            }
        }
    }
    return result;
}

void VectorPath::convertToPainterPath()
{
    if (m_isPainterPath)
        return;
    m_painterPath = toPainterPath();
    m_isPainterPath = true;
}

bool VectorPath::isPainterPath() const
{
    return m_isPainterPath;
}

int VectorPath::pathCount() const
{
    if (m_isPainterPath)
        return m_painterPath.toSubpathPolygons().count();
    else
        return m_polygons.count();
}

QRectF VectorPath::boundingRect() const
{
    if (m_isPainterPath) {
        return m_painterPath.boundingRect();
    } else {
        QRectF result;
        foreach (QPolygonF polygon, m_polygons) {
            result = result.united(polygon.boundingRect());
        }
        return result;
    }
}
