#!/bin/bash

# crontab script that can be executed every night
# to upload resolved cases to OSM
# and dump the database for backup.

cd `dirname $0`

export LD_LIBRARY_PATH=/home/tyndare/.local/lib/ PYTHONPATH=/home/tyndare/.local/lib/python2.7/site-packages/

mkdir -p resolutions-logs
cd resolutions-logs/ && ../resolve_and_upload_to_osm.py 2>&1 > resolve_and_upload_to_osm-`date +%Y-%m-%d`.log

./dump.sh



