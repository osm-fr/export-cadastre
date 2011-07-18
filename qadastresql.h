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

#ifndef QADASTRESQL_H
#define QADASTRESQL_H

#include <QObject>
#include <QThread>
#include <QSqlDatabase>
#include "cadastrewrapper.h"

class QadastreSQL : public QObject
{
    Q_OBJECT
public:
    explicit QadastreSQL(QObject *parent = 0);

signals:

public slots:
    void run();

private slots:
    void importDepartments();
    void importDepartmentCities(const QString &department);
    void convert(const QString &code);

private:
    CadastreWrapper *m_cadastre;
    QList<QString> m_importQueue;
    QSqlDatabase db;
};

#endif // QADASTRESQL_H
