


all:
	cd pdfparser && qmake && make
	cd cadastre_fr_segmented && make
	cd data/segmented_building && make
 

clean:
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
	cd pdfparser && make distclean
	cd cadastre_fr_segmented && make clean
	cd data/segmented_building && make clean
