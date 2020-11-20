

all:Makefile.qt
	make -f Makefile.qt
	install Qadastre2OSM ../

Makefile.qt:Qadastre2OSM.pro
	qmake-qt4 -o Makefile.qt Qadastre2OSM.pro

clean:
	-make -f Makefile.qt clean

distclean:
	-make -f Makefile.qt distclean
	rm -f Makefile.qt
	rm -f Qadastre2OSM



