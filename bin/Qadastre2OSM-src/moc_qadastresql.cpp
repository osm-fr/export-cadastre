/****************************************************************************
** Meta object code from reading C++ file 'qadastresql.h'
**
** Created: Thu Jul 21 23:29:15 2011
**      by: The Qt Meta Object Compiler version 62 (Qt 4.6.3)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "qadastresql.h"
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'qadastresql.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 62
#error "This file was generated using the moc from 4.6.3. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
static const uint qt_meta_data_QadastreSQL[] = {

 // content:
       4,       // revision
       0,       // classname
       0,    0, // classinfo
       4,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: signature, parameters, type, tag, flags
      13,   12,   12,   12, 0x0a,
      19,   12,   12,   12, 0x08,
      50,   39,   12,   12, 0x08,
      87,   82,   12,   12, 0x08,

       0        // eod
};

static const char qt_meta_stringdata_QadastreSQL[] = {
    "QadastreSQL\0\0run()\0importDepartments()\0"
    "department\0importDepartmentCities(QString)\0"
    "code\0convert(QString)\0"
};

const QMetaObject QadastreSQL::staticMetaObject = {
    { &QObject::staticMetaObject, qt_meta_stringdata_QadastreSQL,
      qt_meta_data_QadastreSQL, 0 }
};

#ifdef Q_NO_DATA_RELOCATION
const QMetaObject &QadastreSQL::getStaticMetaObject() { return staticMetaObject; }
#endif //Q_NO_DATA_RELOCATION

const QMetaObject *QadastreSQL::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->metaObject : &staticMetaObject;
}

void *QadastreSQL::qt_metacast(const char *_clname)
{
    if (!_clname) return 0;
    if (!strcmp(_clname, qt_meta_stringdata_QadastreSQL))
        return static_cast<void*>(const_cast< QadastreSQL*>(this));
    return QObject::qt_metacast(_clname);
}

int QadastreSQL::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: run(); break;
        case 1: importDepartments(); break;
        case 2: importDepartmentCities((*reinterpret_cast< const QString(*)>(_a[1]))); break;
        case 3: convert((*reinterpret_cast< const QString(*)>(_a[1]))); break;
        default: ;
        }
        _id -= 4;
    }
    return _id;
}
QT_END_MOC_NAMESPACE
