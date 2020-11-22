


all:
	cd pdfparser && qmake && make
	make -C cadastre_fr_segmented
	make -C data

clean distclean:
	make -C data $@
	rm -f *.pyc
	rm -f cadastre_fr/*.pyc
	rm -f *-*.txt
	rm -f *.pdf
	rm -f *-*.xml
	rm -f *.bbox
	rm -f *.osm
	rm -f *.ok
	rm -f *.zip
	rm -f *.log
	cd pdfparser && make $@
	cd cadastre_fr_segmented && make clean
	find . -type d -name "__pycache__" -exec rm -rf {} \;
	find . -type f -name "*.pyc" -exec rm -f {} \;

