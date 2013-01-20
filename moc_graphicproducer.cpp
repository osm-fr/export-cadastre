/****************************************************************************
** Meta object code from reading C++ file 'graphicproducer.h'
**
** Created: Thu Jul 21 23:29:08 2011
**      by: The Qt Meta Object Compiler version 62 (Qt 4.6.3)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "graphicproducer.h"
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'graphicproducer.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 62
#error "This file was generated using the moc from 4.6.3. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
static const uint qt_meta_data_GraphicProducer[] = {

 // content:
       4,       // revision
       0,       // classname
       0,    0, // classinfo
       5,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       3,       // signalCount

 // signals: signature, parameters, type, tag, flags
      30,   17,   16,   16, 0x05,
      90,   68,   16,   16, 0x05,
     146,  139,   16,   16, 0x05,

 // slots: signature, parameters, type, tag, flags
     186,  169,  164,   16, 0x0a,
     226,  217,  164,   16, 0x0a,

       0        // eod
};

static const char qt_meta_stringdata_GraphicProducer[] = {
    "GraphicProducer\0\0path,context\0"
    "strikePath(VectorPath,GraphicContext)\0"
    "path,context,fillRule\0"
    "fillPath(VectorPath,GraphicContext,Qt::FillRule)\0"
    "result\0parsingDone(bool)\0bool\0"
    "stream,streamLen\0parseStream(const char*,ulong)\0"
    "fileName\0parsePDF(QString)\0"
};

const QMetaObject GraphicProducer::staticMetaObject = {
    { &QObject::staticMetaObject, qt_meta_stringdata_GraphicProducer,
      qt_meta_data_GraphicProducer, 0 }
};

#ifdef Q_NO_DATA_RELOCATION
const QMetaObject &GraphicProducer::getStaticMetaObject() { return staticMetaObject; }
#endif //Q_NO_DATA_RELOCATION

const QMetaObject *GraphicProducer::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->metaObject : &staticMetaObject;
}

void *GraphicProducer::qt_metacast(const char *_clname)
{
    if (!_clname) return 0;
    if (!strcmp(_clname, qt_meta_stringdata_GraphicProducer))
        return static_cast<void*>(const_cast< GraphicProducer*>(this));
    return QObject::qt_metacast(_clname);
}

int GraphicProducer::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: strikePath((*reinterpret_cast< const VectorPath(*)>(_a[1])),(*reinterpret_cast< const GraphicContext(*)>(_a[2]))); break;
        case 1: fillPath((*reinterpret_cast< const VectorPath(*)>(_a[1])),(*reinterpret_cast< const GraphicContext(*)>(_a[2])),(*reinterpret_cast< Qt::FillRule(*)>(_a[3]))); break;
        case 2: parsingDone((*reinterpret_cast< bool(*)>(_a[1]))); break;
        case 3: { bool _r = parseStream((*reinterpret_cast< const char*(*)>(_a[1])),(*reinterpret_cast< ulong(*)>(_a[2])));
            if (_a[0]) *reinterpret_cast< bool*>(_a[0]) = _r; }  break;
        case 4: { bool _r = parsePDF((*reinterpret_cast< const QString(*)>(_a[1])));
            if (_a[0]) *reinterpret_cast< bool*>(_a[0]) = _r; }  break;
        default: ;
        }
        _id -= 5;
    }
    return _id;
}

// SIGNAL 0
void GraphicProducer::strikePath(const VectorPath & _t1, const GraphicContext & _t2)
{
    void *_a[] = { 0, const_cast<void*>(reinterpret_cast<const void*>(&_t1)), const_cast<void*>(reinterpret_cast<const void*>(&_t2)) };
    QMetaObject::activate(this, &staticMetaObject, 0, _a);
}

// SIGNAL 1
void GraphicProducer::fillPath(const VectorPath & _t1, const GraphicContext & _t2, Qt::FillRule _t3)
{
    void *_a[] = { 0, const_cast<void*>(reinterpret_cast<const void*>(&_t1)), const_cast<void*>(reinterpret_cast<const void*>(&_t2)), const_cast<void*>(reinterpret_cast<const void*>(&_t3)) };
    QMetaObject::activate(this, &staticMetaObject, 1, _a);
}

// SIGNAL 2
void GraphicProducer::parsingDone(bool _t1)
{
    void *_a[] = { 0, const_cast<void*>(reinterpret_cast<const void*>(&_t1)) };
    QMetaObject::activate(this, &staticMetaObject, 2, _a);
}
QT_END_MOC_NAMESPACE
