


all:
	cd pdfparser && qmake && make
	make fantoir
 

fantoir:
	mkdir -p fantoir
	for f in  `awk -F/ '//{print $$1}' fantoir.txt |uniq` ; do \
	    wget "http://www2.impots.gouv.fr/documentation/fantoir/$$f" -O fantoir/$$f; \
	    touch fantoir/$$f.ok; \
	done

clean:
	rm -f *.pyc
	rm -f *-*.txt
	rm -f *.pdf
	rm -f *-*.xml
	rm -f *.bbox
	rm -f *.osm
	rm -f *.ok
	rm -f *.zip
	rm -f *.log
