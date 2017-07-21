#-------------------------------------------------
#
# Project created by QtCreator 2010-10-29T20:45:51
#
#-------------------------------------------------

QT       = core network gui sql

TARGET = Qadastre2OSM
CONFIG   += console
CONFIG   -= app_bundle

TEMPLATE = app


SOURCES += main.cpp \
    cadastrewrapper.cpp \
    qadastre.cpp \
    graphicproducer.cpp \
    osmgenerator.cpp \
    vectorpath.cpp \
    timeoutthread.cpp \
    qadastresql.cpp

HEADERS += \
    cadastrewrapper.h \
    qadastre.h \
    graphicproducer.h \
    osmgenerator.h \
    vectorpath.h \
    timeoutthread.h \
    qadastresql.h

LIBS += -ljpeg -lz -lpodofo -lproj -lgeos