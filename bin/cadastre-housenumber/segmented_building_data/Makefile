


OSM=segmented-joined.osm

all: classifier.pickle

classifier.pickle: $(OSM) ../segmented_building_classifier.py 
	../segmented_building_classifier.py *.osm *.zip
	
clean:
	rm -f classifier.pickle
