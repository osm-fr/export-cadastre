


OSM=segmented.osm

.PHONY:all test clean

all: classifier.pickle scaler.pickle 

scaler.pickle classifier.pickle: $(OSM) ../segmented_building_train.py 
	../segmented_building_train.py *segmented.osm *segmented.zip

test:
	../segmented_building_test.py *segmented.osm *segmented.zip
	

clean:
	rm -f classifier.pickle scaler.pickle
	rm -f *-prediction_segmente.osm
	rm -f *-missed.osm
	rm -f *-false.osm

zip:
	for f in *-segmented.osm; do zip `basename "$$f" .osm`.zip "$$f" && rm -f "$$f"; done

unzip:
	for f in *.zip; do unzip "$$f" && rm -f "$$f"; done
