/****************************************************************************
** Meta object code from reading C++ file 'osmgenerator.h'
**
** Created: Thu Jul 21 23:29:10 2011
**      by: The Qt Meta Object Compiler version 62 (Qt 4.6.3)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "osmgenerator.h"
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'osmgenerator.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 62
#error "This file was generated using the moc from 4.6.3. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
static const uint qt_meta_data_OSMGenerator[] = {

 // content:
       4,       // revision
       0,       // classname
       0,    0, // classinfo
       3,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: signature, parameters, type, tag, flags
      27,   14,   13,   13, 0x0a,
      87,   65,   13,   13, 0x0a,
     143,  136,   13,   13, 0x0a,

       0        // eod
};

static const char qt_meta_stringdata_OSMGenerator[] = {
    "OSMGenerator\0\0path,context\0"
    "strikePath(VectorPath,GraphicContext)\0"
    "path,context,fillRule\0"
    "fillPath(VectorPath,GraphicContext,Qt::FillRule)\0"
    "result\0parsingDone(bool)\0"
};

const QMetaObject OSMGenerator::staticMetaObject = {
    { &QObject::staticMetaObject, qt_meta_stringdata_OSMGenerator,
      qt_meta_data_OSMGenerator, 0 }
};

#ifdef Q_NO_DATA_RELOCATION
const QMetaObject &OSMGenerator::getStaticMetaObject() { return staticMetaObject; }
#endif //Q_NO_DATA_RELOCATION

const QMetaObject *OSMGenerator::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->metaObject : &staticMetaObject;
}

void *OSMGenerator::qt_metacast(const char *_clname)
{
    if (!_clname) return 0;
    if (!strcmp(_clname, qt_meta_stringdata_OSMGenerator))
        return static_cast<void*>(const_cast< OSMGenerator*>(this));
    return QObject::qt_metacast(_clname);
}

int OSMGenerator::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: strikePath((*reinterpret_cast< const VectorPath(*)>(_a[1])),(*reinterpret_cast< const GraphicContext(*)>(_a[2]))); break;
        case 1: fillPath((*reinterpret_cast< const VectorPath(*)>(_a[1])),(*reinterpret_cast< const GraphicContext(*)>(_a[2])),(*reinterpret_cast< Qt::FillRule(*)>(_a[3]))); break;
        case 2: parsingDone((*reinterpret_cast< bool(*)>(_a[1]))); break;
        default: ;
        }
        _id -= 3;
    }
    return _id;
}
QT_END_MOC_NAMESPACE
