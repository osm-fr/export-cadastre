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

#include "timeoutthread.h"
#include <iostream>
#include <QCoreApplication>
#include <cstdlib>

TimeoutThread::TimeoutThread(quint32 secs, const QString &message, QObject *parent) :
    QThread(parent), m_secs(secs), m_message(message)
{
}

void TimeoutThread::run()
{
    this->sleep(m_secs);
    std::cerr << m_message.toLocal8Bit().constData() << std::endl;
    // Ouch, I'm a bad guy !
    char *machin = 0;
    machin[42] = 12;
    // Nothing too subtle here : it must stop right now, enough time wasted.
    ::exit(-2);
}
