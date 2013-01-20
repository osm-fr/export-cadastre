/****************************************************************************
** Meta object code from reading C++ file 'cadastrewrapper.h'
**
** Created: Thu Jul 21 23:28:59 2011
**      by: The Qt Meta Object Compiler version 62 (Qt 4.6.3)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "cadastrewrapper.h"
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'cadastrewrapper.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 62
#error "This file was generated using the moc from 4.6.3. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
static const uint qt_meta_data_CadastreWrapper[] = {

 // content:
       4,       // revision
       0,       // classname
       0,    0, // classinfo
       7,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       4,       // signalCount

 // signals: signature, parameters, type, tag, flags
      17,   16,   16,   16, 0x05,
      50,   39,   16,   16, 0x05,
      95,   75,   16,   16, 0x05,
     151,  146,   16,   16, 0x05,

 // slots: signature, parameters, type, tag, flags
     188,  175,   16,   16, 0x08,
     212,  175,   16,   16, 0x08,
     231,  175,   16,   16, 0x08,

       0        // eod
};

static const char qt_meta_stringdata_CadastreWrapper[] = {
    "CadastreWrapper\0\0departmentAvailable()\0"
    "department\0citiesAvailable(QString)\0"
    "code,name,bbox,data\0"
    "cityDownloaded(QString,QString,QString,QIODevice*)\0"
    "name\0downloadFailed(QString)\0networkReply\0"
    "bboxAvailable(QObject*)\0pdfReady(QObject*)\0"
    "cityFound(QObject*)\0"
};

const QMetaObject CadastreWrapper::staticMetaObject = {
    { &QObject::staticMetaObject, qt_meta_stringdata_CadastreWrapper,
      qt_meta_data_CadastreWrapper, 0 }
};

#ifdef Q_NO_DATA_RELOCATION
const QMetaObject &CadastreWrapper::getStaticMetaObject() { return staticMetaObject; }
#endif //Q_NO_DATA_RELOCATION

const QMetaObject *CadastreWrapper::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->metaObject : &staticMetaObject;
}

void *CadastreWrapper::qt_metacast(const char *_clname)
{
    if (!_clname) return 0;
    if (!strcmp(_clname, qt_meta_stringdata_CadastreWrapper))
        return static_cast<void*>(const_cast< CadastreWrapper*>(this));
    return QObject::qt_metacast(_clname);
}

int CadastreWrapper::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: departmentAvailable(); break;
        case 1: citiesAvailable((*reinterpret_cast< const QString(*)>(_a[1]))); break;
        case 2: cityDownloaded((*reinterpret_cast< const QString(*)>(_a[1])),(*reinterpret_cast< const QString(*)>(_a[2])),(*reinterpret_cast< const QString(*)>(_a[3])),(*reinterpret_cast< QIODevice*(*)>(_a[4]))); break;
        case 3: downloadFailed((*reinterpret_cast< const QString(*)>(_a[1]))); break;
        case 4: bboxAvailable((*reinterpret_cast< QObject*(*)>(_a[1]))); break;
        case 5: pdfReady((*reinterpret_cast< QObject*(*)>(_a[1]))); break;
        case 6: cityFound((*reinterpret_cast< QObject*(*)>(_a[1]))); break;
        default: ;
        }
        _id -= 7;
    }
    return _id;
}

// SIGNAL 0
void CadastreWrapper::departmentAvailable()
{
    QMetaObject::activate(this, &staticMetaObject, 0, 0);
}

// SIGNAL 1
void CadastreWrapper::citiesAvailable(const QString & _t1)
{
    void *_a[] = { 0, const_cast<void*>(reinterpret_cast<const void*>(&_t1)) };
    QMetaObject::activate(this, &staticMetaObject, 1, _a);
}

// SIGNAL 2
void CadastreWrapper::cityDownloaded(const QString & _t1, const QString & _t2, const QString & _t3, QIODevice * _t4)
{
    void *_a[] = { 0, const_cast<void*>(reinterpret_cast<const void*>(&_t1)), const_cast<void*>(reinterpret_cast<const void*>(&_t2)), const_cast<void*>(reinterpret_cast<const void*>(&_t3)), const_cast<void*>(reinterpret_cast<const void*>(&_t4)) };
    QMetaObject::activate(this, &staticMetaObject, 2, _a);
}

// SIGNAL 3
void CadastreWrapper::downloadFailed(const QString & _t1)
{
    void *_a[] = { 0, const_cast<void*>(reinterpret_cast<const void*>(&_t1)) };
    QMetaObject::activate(this, &staticMetaObject, 3, _a);
}
QT_END_MOC_NAMESPACE
