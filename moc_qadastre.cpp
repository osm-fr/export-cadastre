/****************************************************************************
** Meta object code from reading C++ file 'qadastre.h'
**
** Created: Thu Jul 21 23:29:05 2011
**      by: The Qt Meta Object Compiler version 62 (Qt 4.6.3)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "qadastre.h"
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'qadastre.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 62
#error "This file was generated using the moc from 4.6.3. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
static const uint qt_meta_data_Qadastre[] = {

 // content:
       4,       // revision
       0,       // classname
       0,    0, // classinfo
       6,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: signature, parameters, type, tag, flags
      21,   10,    9,    9, 0x0a,
      66,   46,    9,    9, 0x0a,
     116,   10,    9,    9, 0x0a,
     151,  136,    9,    9, 0x0a,
     201,  185,    9,    9, 0x0a,
     231,    9,    9,    9, 0x0a,

       0        // eod
};

static const char qt_meta_stringdata_Qadastre[] = {
    "Qadastre\0\0department\0citiesAvailable(QString)\0"
    "code,name,bbox,data\0"
    "cityAvailable(QString,QString,QString,QIODevice*)\0"
    "listCities(QString)\0dept,code,name\0"
    "download(QString,QString,QString)\0"
    "code,name,lands\0convert(QString,QString,bool)\0"
    "run()\0"
};

const QMetaObject Qadastre::staticMetaObject = {
    { &QThread::staticMetaObject, qt_meta_stringdata_Qadastre,
      qt_meta_data_Qadastre, 0 }
};

#ifdef Q_NO_DATA_RELOCATION
const QMetaObject &Qadastre::getStaticMetaObject() { return staticMetaObject; }
#endif //Q_NO_DATA_RELOCATION

const QMetaObject *Qadastre::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->metaObject : &staticMetaObject;
}

void *Qadastre::qt_metacast(const char *_clname)
{
    if (!_clname) return 0;
    if (!strcmp(_clname, qt_meta_stringdata_Qadastre))
        return static_cast<void*>(const_cast< Qadastre*>(this));
    return QThread::qt_metacast(_clname);
}

int Qadastre::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QThread::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: citiesAvailable((*reinterpret_cast< const QString(*)>(_a[1]))); break;
        case 1: cityAvailable((*reinterpret_cast< const QString(*)>(_a[1])),(*reinterpret_cast< const QString(*)>(_a[2])),(*reinterpret_cast< const QString(*)>(_a[3])),(*reinterpret_cast< QIODevice*(*)>(_a[4]))); break;
        case 2: listCities((*reinterpret_cast< const QString(*)>(_a[1]))); break;
        case 3: download((*reinterpret_cast< const QString(*)>(_a[1])),(*reinterpret_cast< const QString(*)>(_a[2])),(*reinterpret_cast< const QString(*)>(_a[3]))); break;
        case 4: convert((*reinterpret_cast< const QString(*)>(_a[1])),(*reinterpret_cast< const QString(*)>(_a[2])),(*reinterpret_cast< const bool(*)>(_a[3]))); break;
        case 5: run(); break;
        default: ;
        }
        _id -= 6;
    }
    return _id;
}
QT_END_MOC_NAMESPACE
