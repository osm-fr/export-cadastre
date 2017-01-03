

# Database management for http://cadastre.openstreetmap.fr/segmented/

## Intro

An analysis is done to predict some buildings that may have been 
segmented by the French cadastre.
(see `../cadastre-housenumber/cadastre_fr/segmented_py`)

The scripts here manage a database used to crowd-source
the confirmation of the segmented cases.

## Database creation

    su - postgres
    createuser cadastre
    psql -c "ALTER ROLE cadastre WITH ENCRYPTED PASSWORD 'XXX'"
    createdb  -T template0 -O cadastre cadastre
    psql -c "create extension postgis;" cadastre
    psql -c "GRANT SELECT,UPDATE,DELETE ON TABLE spatial_ref_sys TO cadastre;" cadastre

    psql cadastre cadastre < segmented.sql

## Password file

The database connection string need to be saved in the file `.database-connection-string`

E.g.:

    `echo "dbname=cadastre user=cadastre password=XXX" > .database-connection-string`

## Database structure

The database structure is an adaptation of the one used by OpenSolarMap
https://github.com/opensolarmap/solback/blob/master/solback.sql

See file `segmented.sql`.

There is one table listing all the predicted segmentation cases.
And one tables to collect contributions from users that will visually 
validate the predictions.


## Prediction

The prediction for segmented building is done on .osm.pbf OpenStreetMap extract.
with the script `pbf_segmented_building_predict.py` specifying the projection to use.

The script `france_pbf_predict.sh` download all .osm.pbf files corresponding
to France regions and run prediction on them.

The generated prediction results can be imported with the script `prediction_import.py`

Exemple:

    wget "http://download.geofabrik.de/europe/france/guadeloupe-latest.osm.pbf"
    ./pbf_segmented_building_predict.py guadeloupe-latest.osm.pbf 32620 | ./prediction_import

## Web Interface

The webinterface located in the web directory allow users to confirm or infirm
predictions.
It will call the script `get.py` to obtain segmentation casess, and script `set.py` to record a validation.

## Resolution

TODO
