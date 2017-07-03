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


#include "cadastrewrapper.h"
#include <iostream>
#include <QUrl>
#include <QRegExp>
#include <QStringList>
#include <QFile>
#include <QDebug>
#include <QCoreApplication>
#include <QNetworkCookieJar>
#include <QProcessEnvironment>
#include <QNetworkProxy>

CadastreWrapper::CadastreWrapper(QObject *parent) :
    QObject(parent)
{
    m_nam = new QNetworkAccessManager(this);

    QString httpProxyEnv = QProcessEnvironment::systemEnvironment().value("http_proxy");
    if(!httpProxyEnv.isEmpty()) {
        QUrl url(httpProxyEnv);
        QString userName = url.userName();
        QString password = url.password();
        QString hostName = url.host();
        quint16 port = url.port();
        QNetworkProxy proxy(QNetworkProxy::HttpProxy, hostName, port, userName, password);
        m_nam->setProxy(proxy);
    }

    m_departmentsRequest = 0;

    // Get a cookie and CSRF_TOKEN
    QNetworkReply* initialRequest = m_nam->get(QNetworkRequest(QUrl("https://www.cadastre.gouv.fr/scpc/rechercherPlan.do")));
    QEventLoop loop;
    connect(initialRequest, SIGNAL(finished()), &loop, SLOT(quit()));
    loop.exec();
    m_token = parse_token(initialRequest);
    //qDebug() << "CSRF_TOKEN = " << m_token;

    connect(&m_citiesSignalMapper, SIGNAL(mapped(QString)), this, SIGNAL(citiesAvailable(QString)));
    connect(&m_bboxSignalMapper, SIGNAL(mapped(QObject*)), this, SLOT(bboxAvailable(QObject*)));
    connect(&m_pdfSignalMapper, SIGNAL(mapped(QObject*)), this, SLOT(pdfReady(QObject*)));
    connect(&m_citySearchMapper, SIGNAL(mapped(QObject*)), this, SLOT(cityFound(QObject*)));
}

QString CadastreWrapper::parse_token(QNetworkReply* networkReply)
{
    if (networkReply->isFinished() && (networkReply->error()==0)) {
        QString html = QString::fromUtf8(networkReply->readAll());
        QRegExp tokenParesr("CSRF_TOKEN=(.*)['\" ]");
        tokenParesr.setMinimal(true);
        tokenParesr.indexIn(html);
        return tokenParesr.cap(1);
    } else {
        std::cerr << "ERROR: connecting to www.cadastre.gouv.fr" << std::endl;
        return "";
    }
}

void CadastreWrapper::requestDepartmentList()
{
    if ((m_departments.count() == 0) && (!m_departmentsRequest)) {
        m_departmentsRequest = m_nam->get(QNetworkRequest(QUrl("https://www.cadastre.gouv.fr/scpc/accueil.do")));
        connect(m_departmentsRequest, SIGNAL(finished()), this, SIGNAL(departmentAvailable()));
    } else if (m_departments.count() > 0)
        emit departmentAvailable();
}

QMap<QString, QString> CadastreWrapper::listDepartments()
{
    if (m_departmentsRequest && (m_departments.count() == 0)) {
        // Parse the answer
        QRegExp optParser("<option value=\"(\\w+)\">(.*)</option>");
        optParser.setMinimal(true);
        QString code = QString::fromUtf8(m_departmentsRequest->readAll());
        QString options = code.split("<select name=\"codeDepartement\"")[1].split("</select>")[0];
        int pos = 0;
        while ((pos = optParser.indexIn(options, pos)) != -1) {
            m_departments[optParser.cap(1)] = optParser.cap(2);
            pos += optParser.matchedLength();
        }
        m_departmentsRequest->deleteLater();
        m_departmentsRequest = 0;
    }
    return m_departments;
}

void CadastreWrapper::requestCities(const QString &department)
{
    while (m_nam->cookieJar()->cookiesForUrl(QUrl("https://www.cadastre.gouv.fr/scpc")).count() == 0)
        qApp->processEvents();
    QString url = QString("https://www.cadastre.gouv.fr/scpc/listerCommune.do?CSRF_TOKEN=%1&codeDepartement=%2&libelle=&keepVolatileSession=&offset=5000").arg(m_token, department);
    QNetworkReply *req = m_nam->get(QNetworkRequest(url));
    m_citiesSignalMapper.setMapping(req, department);
    connect(req, SIGNAL(finished()), &m_citiesSignalMapper, SLOT(map()));
    m_citiesRequest[department] = req;
}

QMap<QString, QString> CadastreWrapper::listCities(const QString &department)
{
    if ((m_citiesRequest.contains(department)) && (m_cities[department].count() == 0)) {
        QRegExp tableExtractor("<table.*class=\"resonglet\".*>(.*)</table>");
        QRegExp titleExtractor("<strong>(.*) </strong>");
        QRegExp codeExtractor("ajoutArticle\\('(\\w*)',");
        tableExtractor.setMinimal(true);
        codeExtractor.setMinimal(true);
        QString code = QString::fromUtf8(m_citiesRequest[department]->readAll());
        QStringList tables;
        int pos = 0;
        while ((pos = tableExtractor.indexIn(code, pos)) != -1) {
            tables.append(tableExtractor.cap(1));
            pos += tableExtractor.matchedLength();
        }
        foreach(QString table, tables) {
            // Only vectorial communes are required
            if (!table.contains("VECT")) {
                continue;
            }
            if (titleExtractor.indexIn(table) != -1) {
                if (codeExtractor.indexIn(table) != -1) {
                    m_cities[department][codeExtractor.cap(1)] = titleExtractor.cap(1).replace("&#039;","'");
                }
            }
        }
        m_citiesRequest[department]->deleteLater();
        m_citiesRequest.remove(department);
    }
    return m_cities[department];
}

void CadastreWrapper::requestPDF(const QString &dept, const QString &cityCode, const QString &cityName)
{
    while (m_nam->cookieJar()->cookiesForUrl(QUrl("https://www.cadastre.gouv.fr/scpc")).count() == 0)
        qApp->processEvents();

    QString url = "https://www.cadastre.gouv.fr/scpc/rechercherPlan.do";
    QString postData = QString("numeroVoie=&indiceRepetition=&nomVoie=&lieuDit=&ville=%1&codePostal=&codeDepartement=%2&nbResultatParPage=100&x=31&y=11&CSRF_TOKEN=%3").arg(QString::fromLatin1(QUrl::toPercentEncoding(cityName)), dept, m_token);

    qDebug() << postData;
    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/x-www-form-urlencoded");
    QNetworkReply *req = m_nam->post(request, postData.toLatin1());
    req->setProperty("cityCode", cityCode);
    req->setProperty("cityName", cityName);
    req->setProperty("dept", dept);
    m_citySearchMapper.setMapping(req, req);
    connect(req, SIGNAL(finished()), &m_citySearchMapper, SLOT(map()));
}

void CadastreWrapper::bboxAvailable(QObject *networkReply)
{
    qDebug() << "bboxAvailable";
    QNetworkReply *rep = qobject_cast<QNetworkReply*>(networkReply);
    if (!rep)
        return;
    QString cityCode = rep->property("cityCode").toString();
    QString cityName = rep->property("cityName").toString();
    QString dept = rep->property("dept").toString();

    // Search the bounding box
    QRegExp projExtracton("<span[^>]*id=\"projectionName\"[^>]*>(.*)</span>");
    projExtracton.setMinimal(true);
    QRegExp bbExtractor("new GeoBox\\(\n\t*(\\d*\\.\\d*),\n\t*(\\d*\\.\\d*),\n\t*(\\d*\\.\\d*),\n\t*(\\d*\\.\\d*)\\)");
    QString pageCode = rep->readAll();
    if ((projExtracton.indexIn(pageCode) != -1) && (bbExtractor.indexIn(pageCode) != -1)) {
        QString bbox = QString("%1,%2,%3,%4").arg(bbExtractor.cap(1)).arg(bbExtractor.cap(2)).arg(bbExtractor.cap(3)).arg(bbExtractor.cap(4));
        // Now we have everything needed to request the PDF !
        QString postData = QString("WIDTH=%1&HEIGHT=%2&MAPBBOX=%3&SLD_BODY=&RFV_REF=%4").arg(90000).arg(90000).arg(bbox).arg(cityCode);
        QString url = QString("https://www.cadastre.gouv.fr/scpc/imprimerExtraitCadastralNonNormalise.do?CSRF_TOKEN=%1").arg(m_token);
        QNetworkRequest request(url);
        request.setHeader(QNetworkRequest::ContentTypeHeader, "application/x-www-form-urlencoded");
        QNetworkReply *pdfRep = m_nam->post(request, postData.toLocal8Bit());
        pdfRep->setProperty("cityCode", cityCode);
        QString proj = projExtracton.cap(1).trimmed();
        if (dept == "971")
        {
            if (cityCode.endsWith("123" /*SAINT BARTHELEMY (ILE)*/) ||
                cityCode.endsWith("127" /*SAINT MARTIN*/))
            {
                qDebug() << "projection corrigee de " + proj + " vers GUADFM49U20";
                proj = "GUADFM49U20";
            }
        }
        pdfRep->setProperty("cityName", cityName);
        pdfRep->setProperty("boundingBox", proj + ":" + bbox);
        m_pdfSignalMapper.setMapping(pdfRep, pdfRep);
        connect(pdfRep, SIGNAL(finished()), &m_pdfSignalMapper, SLOT(map()));
    } else {
        qDebug() << pageCode;
        qFatal("Invalid page for bounding box ?");

    }
}

void CadastreWrapper::pdfReady(QObject *networkReply)
{
    QNetworkReply *rep = qobject_cast<QNetworkReply*>(networkReply);

    if (!rep)
        return;
    QString cityCode = rep->property("cityCode").toString();
    QString cityName = rep->property("cityName").toString();
    QString bbox = rep->property("boundingBox").toString();

    if (rep->header(QNetworkRequest::ContentTypeHeader).toString().contains("pdf")) {
        emit cityDownloaded(cityCode, cityName, bbox, rep);
    } else {
        qDebug() << rep->readAll();
        emit downloadFailed(cityName);
    }
}



void CadastreWrapper::cityFound(QObject *networkReply)
{
    qDebug() << "city found ?";
    QNetworkReply *rep = qobject_cast<QNetworkReply*>(networkReply);

    if (!rep)
        return;
    //qDebug() << rep->readAll();
    QString cityCode = rep->property("cityCode").toString();
    QString cityName = rep->property("cityName").toString();
    QString dept = rep->property("dept").toString();

    QString url = QString("https://www.cadastre.gouv.fr/scpc/afficherCarteCommune.do?CSRF_TOKEN=%1&c=%2&dontSaveLastForward&keepVolatileSession=").arg(m_token, cityCode);
    QNetworkReply *req = m_nam->get(QNetworkRequest(url));
    req->setProperty("cityCode", cityCode);
    req->setProperty("cityName", cityName);
    req->setProperty("dept", dept);
    m_bboxSignalMapper.setMapping(req, req);
    connect(req, SIGNAL(finished()), &m_bboxSignalMapper, SLOT(map()));
}
