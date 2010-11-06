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

#ifndef QADASTRE_H
#define QADASTRE_H

#include <QObject>
#include <QString>
#include "cadastrewrapper.h"

class Qadastre : public QObject
{
    Q_OBJECT
public:
    explicit Qadastre(QObject *parent = 0);


signals:

public slots:
    void citiesAvailable(const QString &department);
    void cityAvailable(const QString &code, const QString &name, const QString &bbox, QIODevice *data);
    void listCities(const QString &department);
    void download(const QString &dept, const QString &code, const QString &name);
    void convert(const QString &code, const QString &name);
    void execute();

private:
    CadastreWrapper *m_cadastre;
};

#endif // QADASTRE_H
