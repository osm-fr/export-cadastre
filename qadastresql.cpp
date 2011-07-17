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
#include <QSqlDatabase>
#include <QSqlQuery>
#include <QSqlError>
#include <QDebug>
#include <QCoreApplication>
#include <QStringList>

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
    insertCity.prepare("INSERT INTO cities(department, \"code\", name) VALUES (:dept, :code, :name);");
    QMap<QString, QString> cities = m_cadastre->listCities(department);
    qDebug() << cities << "for" << department;
    QMap<QString, QString>::const_iterator cityIterator = cities.constBegin();
    while (cityIterator != cities.constEnd())
    {
        qDebug() << "Inserting one city ?";
        insertCity.bindValue(":dept", department);
        insertCity.bindValue(":code", cityIterator.key());
        insertCity.bindValue(":name", cityIterator.value());
        if (!insertCity.exec())
        {
            qDebug() << "Failed !";
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

    if ((arguments.length() == 1) && (arguments[0] == "--initial-import"))
    {
        qDebug() << "Launching initial import : listing all departments from qadastre, then all cities";
        connect(m_cadastre, SIGNAL(departmentAvailable()), this, SLOT(importDepartments()));
        connect(m_cadastre, SIGNAL(citiesAvailable(QString)), this, SLOT(importDepartmentCities(QString)));
        m_cadastre->requestDepartmentList();
    }
}
