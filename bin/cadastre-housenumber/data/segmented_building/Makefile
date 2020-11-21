

OSM=segmented.osm not_segmented.osm 
DOWNLOAD_ZIP=BOURG-LES-VALENCE-houses-simplifie-segmented.zip  LORIENT-houses-simplifie-segmented.zip  PORTES-LES-VALENCE-houses-simplifie-segmented.zip  TAIN-houses-simplifie-segmented.zip
INPUT=$(OSM) $(DOWNLOAD_ZIP)

TRAIN=../../bin/osm_segmented_building_train.py 

.PHONY:all test clean

all: 3
	
2: classifier.pickle2 scaler.pickle2

3: scaler.pickle3 classifier.pickle3

scaler.pickle2 classifier.pickle2: $(TRAIN) $(INPUT) 
	python2 $^

scaler.pickle3 classifier.pickle3: $(TRAIN) $(INPUT) 
	python3 $^

$(DOWNLOAD_ZIP):
	wget "http://cadastre.openstreetmap.fr/segmented_building_data/$@"

test:
	../../bin/osm_segmented_building_test.py *segmented.osm *segmented.zip

clean:
	rm -f classifier.pickle* scaler.pickle*
	rm -f *-prediction_segmente.osm
	rm -f *-missed.osm
	rm -f *-false.osm

zip:
	for f in *-segmented.osm; do zip `basename "$$f" .osm`.zip "$$f" && rm -f "$$f"; done

unzip:
	for f in *.zip; do unzip "$$f" && rm -f "$$f"; done

