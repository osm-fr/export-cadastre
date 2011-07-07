#ifndef QADASTRESQL_H
#define QADASTRESQL_H

#include <QObject>
#include <QThread>
#include <QSqlDatabase>
#include "cadastrewrapper.h"

class QadastreSQL : public QObject//QThread
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

private:
    CadastreWrapper *m_cadastre;
    QList<QString> m_importQueue;
    QSqlDatabase db;
};

#endif // QADASTRESQL_H
