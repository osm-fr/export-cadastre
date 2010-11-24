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


#include "qadastre.h"
#include <QCoreApplication>
#include <iostream>
#include <QDebug>
#include <QFile>
#include <QTimer>
#include <QStringList>
#include "osmgenerator.h"
#include "graphicproducer.h"
#include "timeoutthread.h"

Qadastre::Qadastre(QObject *parent) :
    QThread(parent)
{
    m_cadastre = 0;
}

void Qadastre::citiesAvailable(const QString &department)
{
    if (!m_cadastre)
        return;
    QMap<QString, QString> cities = m_cadastre->listCities(department);
    if (cities.count() > 0) {
        QMap<QString, QString>::const_iterator i;
        for (i = cities.constBegin() ; i != cities.constEnd() ; ++i)
            std::cout << QString("%1 - %2").arg(i.key(), i.value()).toLocal8Bit().constData() << std::endl;
        qApp->exit(0);
    } else {
        std::cerr << "No city found." << std::endl;
        qApp->exit(-1);
    }
}

void Qadastre::listCities(const QString &department)
{
    if (!m_cadastre)
        return;
    connect(m_cadastre, SIGNAL(citiesAvailable(QString)), this, SLOT(citiesAvailable(QString)));
    m_cadastre->requestCities(department);
}

void Qadastre::cityAvailable(const QString &code, const QString &name, const QString &bbox, QIODevice *data)
{
    qDebug() << "City downloaded";
    qDebug() << code << name << bbox;
    QFile targetBBox(QString("%1-%2.bbox").arg(code, name));
    if (!targetBBox.open(QIODevice::WriteOnly)) {
        qDebug() << "Impossible to write the bbox !";
        qApp->exit(-1);
    }
    targetBBox.write(bbox.toLocal8Bit());
    targetBBox.close();

    QFile targetPDF(QString("%1-%2.pdf").arg(code, name));
    if (!targetPDF.open(QIODevice::WriteOnly)) {
        qDebug() << "Impossible to write the pdf !";
        qApp->exit(-1);
    }
    targetPDF.write(data->readAll());
    targetPDF.close();

    qApp->exit(0);
}

void Qadastre::download(const QString &dept, const QString &code, const QString &name)
{
    if (!m_cadastre)
        return;
    connect(m_cadastre, SIGNAL(cityDownloaded(QString,QString,QString,QIODevice*)), this, SLOT(cityAvailable(QString,QString,QString,QIODevice*)));
    qDebug() << "download city";
    m_cadastre->requestPDF(dept, code, name);
}

void Qadastre::convert(const QString &code, const QString &name)
{
    qRegisterMetaType<VectorPath>("VectorPath");
    qRegisterMetaType<GraphicContext>("GraphicContext");
    qRegisterMetaType<Qt::FillRule>("Qt::FillRule");

    QString pdfName = QString("%1-%2.pdf").arg(code, name);
    QString bboxName = QString("%1-%2.bbox").arg(code, name);
    if ((!QFile::exists(pdfName)) || !QFile::exists(bboxName)) {
        std::cerr << "Download the data first" << std::endl;
        qApp->exit(-1);
        return;
    }

    QFile bboxReader(bboxName);
    bboxReader.open(QIODevice::ReadOnly);
    QString bbox = bboxReader.readAll();
    bboxReader.close();

    GraphicProducer *gp = new GraphicProducer();
    OSMGenerator *og = new OSMGenerator(bbox);
    connect(gp, SIGNAL(fillPath(VectorPath,GraphicContext,Qt::FillRule)), og, SLOT(fillPath(VectorPath,GraphicContext,Qt::FillRule)));
    connect(gp, SIGNAL(strikePath(VectorPath,GraphicContext)), og, SLOT(strikePath(VectorPath,GraphicContext)));
    connect(gp, SIGNAL(parsingDone(bool)), og, SLOT(parsingDone(bool)));
    gp->parsePDF(pdfName);
    gp->deleteLater();

    og->dumpOSMs(QString("%1-%2").arg(code, name));
    og->deleteLater();
}

void Qadastre::run()
{
    if ((qApp->arguments().length() == 3)  && (qApp->arguments()[1] == "--list")) {
        m_cadastre = new CadastreWrapper;
        listCities(qApp->arguments()[2]);
    } else if ((qApp->arguments().length() == 5)  && (qApp->arguments()[1] == "--download")) {
        m_cadastre = new CadastreWrapper;
        (new TimeoutThread(15*60, "Timeout on download", this))->start();
        download(qApp->arguments()[2], qApp->arguments()[3], qApp->arguments()[4]);
    } else if ((qApp->arguments().length() == 4)  && (qApp->arguments()[1] == "--convert")) {
        m_cadastre = new CadastreWrapper;
        (new TimeoutThread(120*60, "Timeout on convert", this))->start();
        convert(qApp->arguments()[2], qApp->arguments()[3]);
        qApp->exit(0);
    } else {
        std::cout << "Usage : " << std::endl;
        std::cout << qApp->argv()[0] << " --list DEPT : list the cities of a department (given its code in a three digit form)" << std::endl;
        std::cout << qApp->argv()[0] << " --download DEPT CODE NAME : download a city" << std::endl;
        std::cout << qApp->argv()[0] << " --convert CODE NAME : generate the .osm files for a city" << std::endl;
        qApp->exit(-1);
    }
    if (m_cadastre)
        m_cadastre->deleteLater();
}
