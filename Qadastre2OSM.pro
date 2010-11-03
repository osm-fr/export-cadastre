#-------------------------------------------------
#
# Project created by QtCreator 2010-10-29T20:45:51
#
#-------------------------------------------------

QT       += core network gui

TARGET = Qadastre2OSM
CONFIG   += console
CONFIG   -= app_bundle

TEMPLATE = app


SOURCES += main.cpp \
    cadastrewrapper.cpp \
    qadastre.cpp \
    graphicproducer.cpp \
    osmgenerator.cpp \
    vectorpath.cpp

HEADERS += \
    cadastrewrapper.h \
    qadastre.h \
    graphicproducer.h \
    osmgenerator.h \
    vectorpath.h

LIBS += -lpodofo -lproj
