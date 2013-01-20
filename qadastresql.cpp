/* This file is part of Qadastre
 * Copyright (C) 2011 Pierre Ducroquet <pinaraf@pinaraf.info>
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

#include "qadastresql.h"
#include "cadastrewrapper.h"
#include "osmgenerator.h"
#include "timeoutthread.h"

#include <QSqlDatabase>
#include <QSqlQuery>
#include <QSqlError>
#include <QEventLoop>
#include <QDebug>
#include <QCoreApplication>
#include <QStringList>
#include <QFile>
#include <iostream>

QadastreSQL::QadastreSQL(QObject *parent) :
    QObject(parent)
{
}

void QadastreSQL::importDepartments()
{
    // Import them in database
    db.transaction();
    QSqlQuery insertDepartment;
    insertDepartment.prepare("INSERT INTO departments(\"number\", name) VALUES (:number, :name);");
    QMap<QString, QString> depts = m_cadastre->listDepartments();
    QMap<QString, QString>::const_iterator deptIterator = depts.constBegin();
    while (deptIterator != depts.constEnd())
    {
        insertDepartment.bindValue(":number", deptIterator.key());
        m_importQueue << deptIterator.key();
        QString name = deptIterator.value();
        name = name.mid(name.indexOf(" - ") + 3);
        insertDepartment.bindValue(":name", name);
        insertDepartment.exec();
        deptIterator++;
    }
    db.commit();

    // Now, we will request the cities
    m_cadastre->requestCities(m_importQueue.takeFirst());
}

void QadastreSQL::importDepartmentCities(const QString &department)
{
    qDebug() << "Importing one department";

    // Import them in database
    db.transaction();
    QSqlQuery insertCity;
    insertCity.prepare("INSERT INTO cities(department, \"code\", name, post_code) VALUES (:dept, :code, :name, :post_code);");
    QMap<QString, QString> cities = m_cadastre->listCities(department);
    qDebug() << cities << "for" << department;
    QMap<QString, QString>::const_iterator cityIterator = cities.constBegin();
    while (cityIterator != cities.constEnd())
    {
        qDebug() << "Inserting one city ?";
        insertCity.bindValue(":dept", department);
        insertCity.bindValue(":code", cityIterator.key());
        QString cityName = cityIterator.value();
        int lastParent = cityName.lastIndexOf('(');
        insertCity.bindValue(":name", cityName.left(lastParent - 1));
        insertCity.bindValue(":post_code", cityName.mid(lastParent + 1, cityName.length() - lastParent - 2));
        if (!insertCity.exec())
        {
            qDebug() << "Failed !";
            qDebug() << insertCity.lastError();
            qFatal("SQL failure");
        }
        cityIterator++;
    }
    db.commit();

    if (!m_importQueue.isEmpty())
    {
        qDebug() << "Requesting another batch";
        m_cadastre->requestCities(m_importQueue.takeFirst());
    }
    else
    {
        qApp->exit(0);
    }
}

void QadastreSQL::convert(const QString &code)
{

    db.transaction();

    QSqlQuery findCity;
    findCity.prepare("SELECT id, name FROM cities WHERE code=:code;");
    findCity.bindValue(":code", code);
    if ((!findCity.exec()) || (!findCity.next()))
    {
        qFatal("Could not get city informations");
        return;
    }
    QString name = findCity.value(1).toString();
    int cityId = findCity.value(0).toInt();
    findCity.finish();

    // Get a new import id
    QSqlQuery insertImport;
    insertImport.prepare("INSERT INTO imports (city) VALUES (:cityId) RETURNING id");
    insertImport.bindValue(":cityId", cityId);
    if ((!insertImport.exec()) || (!insertImport.next()))
    {
        qFatal("Could not get an import id");
        return;
    }

    int importId = insertImport.value(0).toInt();

    qRegisterMetaType<VectorPath>("VectorPath");
    qRegisterMetaType<GraphicContext>("GraphicContext");
    qRegisterMetaType<Qt::FillRule>("Qt::FillRule");

    QString pdfName = QString("%1-%2.pdf").arg(code, name);
    QString bboxName = QString("%1-%2.bbox").arg(code, name);
    if ((!QFile::exists(pdfName)) || !QFile::exists(bboxName)) {
        qDebug() << pdfName;
        std::cerr << "Download the data first" << std::endl;
        qApp->exit(-1);
        qFatal("Dead");
        return;
    }

    QFile bboxReader(bboxName);
    bboxReader.open(QIODevice::ReadOnly);
    QString bbox = bboxReader.readAll();
    bboxReader.close();

    GraphicProducer *gp = new GraphicProducer();
    OSMGenerator *og = new OSMGenerator(bbox, false, this);
    connect(gp, SIGNAL(fillPath(VectorPath,GraphicContext,Qt::FillRule)), og, SLOT(fillPath(VectorPath,GraphicContext,Qt::FillRule)));
    connect(gp, SIGNAL(strikePath(VectorPath,GraphicContext)), og, SLOT(strikePath(VectorPath,GraphicContext)));
    connect(gp, SIGNAL(parsingDone(bool)), og, SLOT(parsingDone(bool)));
    gp->parsePDF(pdfName);
    gp->deleteLater();

    og->dumpSQLs(db, cityId, importId);
    db.commit();

    og->deleteLater();
    qDebug() << "Over !";
    qApp->exit(0);
}

void QadastreSQL::run()
{
    db = QSqlDatabase::addDatabase("QPSQL");
    db.setHostName("localhost");
    db.setDatabaseName("cadastre");
    db.setUserName("moi");
    db.setPassword("moi");
    bool ok = db.open();
    if (!ok)
    {
        qFatal("Unable to connect to database");
    }

    m_cadastre = new CadastreWrapper;
    QStringList arguments = qApp->arguments();
    arguments.removeAll("--sql");
    arguments.removeFirst();

    qDebug() << "Args : " << arguments;
    if ((arguments.length() == 1) && (arguments[0] == "--initial-import"))
    {
        qDebug() << "Launching initial import : listing all departments from qadastre, then all cities";
        connect(m_cadastre, SIGNAL(departmentAvailable()), this, SLOT(importDepartments()));
        connect(m_cadastre, SIGNAL(citiesAvailable(QString)), this, SLOT(importDepartmentCities(QString)));
        m_cadastre->requestDepartmentList();
        QEventLoop loop;
        qApp->exit(loop.exec());
    } else if ((arguments.length() == 2)  && (arguments[0] == "--convert")) {
        /*QThread *tthread = new TimeoutThread(120*60, "Timeout on convert");
        tthread->start();
        connect(qApp, SIGNAL(aboutToQuit()), tthread, SLOT(terminate()));*/
        convert(arguments[1]);
        qApp->exit(0);
    } else {
        qDebug() << "Ye no parlado your langue";
    }
}
