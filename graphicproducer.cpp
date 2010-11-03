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


#include "graphicproducer.h"
#include <QRegExp>
#include <QDebug>
#include <QList>
#include <podofo/PdfDictionary.h>
#include <podofo/PdfObject.h>
#include <podofo/PdfParser.h>
#include <podofo/PdfStream.h>
#include <podofo/PdfVecObjects.h>
#include "vectorpath.h"
#include <cstdlib>
#include <errno.h>

GraphicProducer::GraphicProducer(QObject *parent) :
    QObject(parent)
{
}

bool GraphicProducer::parsePDF(const QString &fileName) {
    PoDoFo::PdfVecObjects objects;
    PoDoFo::PdfParser parser(&objects, fileName.toLocal8Bit());
    PoDoFo::TIVecObjects it = objects.begin();
    bool result = false;
    do {
        PoDoFo::PdfObject *obj = (*it);
        if (obj->HasStream() && (obj->GetObjectLength() > 10000)) {
            PoDoFo::PdfStream *stream = obj->GetStream();
            char *buffer;
            PoDoFo::pdf_long bufferLen;
            stream->GetFilteredCopy(&buffer, &bufferLen);
            qDebug() << "Buffer length : " << bufferLen;
            if (bufferLen > 1000)
                result = parseStream(buffer, bufferLen);
            free(buffer);
        }
        it++;
    } while (it != objects.end());
    emit parsingDone(result);
    return result;
}

bool GraphicProducer::parseStream(const char *stream, unsigned long streamLen) {
    qDebug() << "GraphicProducer::parse";

    //QList<double> stack;
    double stack[200];
    int stackPosition = -1;
    QList<GraphicContext> contexts;
    GraphicContext currentContext;
    currentContext.brush.setStyle(Qt::SolidPattern);
    currentContext.brush.setColor(Qt::black);
    currentContext.pen.setStyle(Qt::SolidLine);
    currentContext.pen.setColor(Qt::black);

    VectorPath currentPath;

    QVector<double> lastArray;

    unsigned long previousPosition = 0;
    unsigned long tokenPosition = 0;
    bool inArray = false;

    double x, y, x1, y1, x2, y2, x3, y3, capStyle, offset, joinStyle;
    do {
        // Special case : array handling
        if (stream[tokenPosition] == '[') {
            inArray = true;
            tokenPosition++;
            previousPosition = tokenPosition;
            continue;
        }
        if ((stream[tokenPosition] != ' ') && (stream[tokenPosition] != '\n') && (stream[tokenPosition] != '\0') && (stream[tokenPosition] != '\t') && (stream[tokenPosition] != ']')) {
            tokenPosition++;
            continue;
        }
        if (previousPosition != tokenPosition) {
            switch (stream[previousPosition]) {
            case 'l':
                y = stack[stackPosition--];
                x = stack[stackPosition--];
                currentPath.lineTo(x, y);
                break;
            case 'v':
                y3 = stack[stackPosition--];
                x3 = stack[stackPosition--];
                y2 = stack[stackPosition--];
                x2 = stack[stackPosition--];
                currentPath.quadTo(x2, y2, x3, y3);
                break;
            case 'm':
                y = stack[stackPosition--];
                x = stack[stackPosition--];
                currentPath.moveTo(x, y);
                break;
            case 'h':
                currentPath.closeSubpath();
                break;
            case 'W':
                if (currentContext.clipPath.length() == 0)
                    currentContext.clipPath = currentPath.toPainterPath();
                if (stream[previousPosition+1] == '*') {
                    currentContext.clipPath.setFillRule(Qt::OddEvenFill);
                    currentPath.setFillRule(Qt::OddEvenFill);
                } else {
                    currentContext.clipPath.setFillRule(Qt::WindingFill);
                    currentPath.setFillRule(Qt::WindingFill);
                }
                currentContext.clipPath = currentContext.clipPath.intersected(currentPath.toPainterPath());
                break;
            case 'n':
                currentPath = VectorPath();
                break;
            case 'q':
                contexts.append(currentContext);
                break;
            case 'Q':
                currentContext = contexts.takeLast();
                break;
            case 'S':
                emit strikePath(currentPath, currentContext);
                currentPath = VectorPath();
                break;
            case 'w':
                currentContext.pen.setWidthF(stack[stackPosition--]);
                break;
            case 'R':
                if (stream[previousPosition+1] == 'G') {
                    double b = stack[stackPosition--];
                    double g = stack[stackPosition--];
                    double r = stack[stackPosition--];
                    currentContext.pen.setColor(QColor(r*255, g*255, b*255));
                }
                break;
            case 'J':
                capStyle = stack[stackPosition--];
                if (capStyle == 0)
                    currentContext.pen.setCapStyle(Qt::FlatCap);
                else if (capStyle == 1)
                    currentContext.pen.setCapStyle(Qt::RoundCap);
                else
                    currentContext.pen.setCapStyle(Qt::SquareCap);
                break;
            case 'M':
                currentContext.pen.setMiterLimit(stack[stackPosition--]);
                break;
            case 'f':
                if (stream[previousPosition+1] == '*')
                    emit fillPath(currentPath, currentContext, Qt::OddEvenFill);
                else
                    emit fillPath(currentPath, currentContext, Qt::WindingFill);
                currentPath = VectorPath();
                break;
            case 'd':
                offset = stack[stackPosition--];
                if (lastArray.count() == 0) {
                    currentContext.pen.setStyle(Qt::SolidLine);
                } else {
                    currentContext.pen.setDashOffset(offset);
                    currentContext.pen.setDashPattern(lastArray);
                    lastArray.clear();
                }
                break;
            case 'r':
                if (stream[previousPosition+1] == 'g') {
                    double b = stack[stackPosition--];
                    double g = stack[stackPosition--];
                    double r = stack[stackPosition--];
                    currentContext.brush.setColor(QColor(r*255, g*255, b*255));
                }
                break;
            case 'c':
                y3 = stack[stackPosition--];
                x3 = stack[stackPosition--];
                y2 = stack[stackPosition--];
                x2 = stack[stackPosition--];
                y1 = stack[stackPosition--];
                x1 = stack[stackPosition--];
                currentPath.cubicTo(x1, y1, x2, y2, x3, y3);
                break;
            case 'j':
                joinStyle = stack[stackPosition--];
                if (joinStyle  == 0)
                    currentContext.pen.setJoinStyle(Qt::MiterJoin);
                else if (joinStyle  == 1)
                    currentContext.pen.setJoinStyle(Qt::RoundJoin);
                else
                    currentContext.pen.setJoinStyle(Qt::BevelJoin);
                break;
            default:
                // handle a number then
                errno = 0;
                double d = strtod(stream + previousPosition, NULL);
                if (errno != 0)
                    qFatal("Convertion to double failed !");
                if (inArray)
                    lastArray << d;
                else
                    stack[++stackPosition] = d;
            }
        }
        previousPosition = tokenPosition + 1;
        if (stream[tokenPosition] == ']') {
            inArray = false;
        }
        tokenPosition++;
    } while (tokenPosition <= streamLen);

    qDebug() << "GraphicProducer::parse done";
    qDebug() << stack; // check empty ?
    return true;
}
