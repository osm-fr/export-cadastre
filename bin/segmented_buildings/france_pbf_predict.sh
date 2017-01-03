#!/bin/bash
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with it. If not, see <http://www.gnu.org/licenses/>.


# Download all pbf file for France regions
# apply segmented building prediction on them
# generate raw output or osmose xml if --osmose option is used..

RESULT_DIR=.
PREDICT=`dirname $0`/pbf_segmented_building_predict.py $1
OSMOSE_POST=`dirname $0`/osmose_post.py
SEGMENTED_DATA_DIR=`dirname $0`/../cadastre-housenumber/data/segmented_building/
OSMOSE_CONF=`dirname $0`/osmose.conf
if [ -z "$TMP" ] ; then
    TMP=/tmp
fi
DOWNLOAD_DIR=$TMP

function list_regions {

    # list regions in inceasing size order 
    # to be sure that the downoald | predict pipe 
    # will always be filled in

    (while read region projection ; do
        echo $region $projection
     done
) << EOT
        mayotte 32738
        guyane 2972
        corse 2154
        martinique 32620
        guadeloupe 32620
        reunion 2975
        limousin 2154
        champagne-ardenne 2154
        haute-normandie 2154
        franche-comte 2154
        basse-normandie 2154
        picardie 2154
        alsace 2154
        auvergne 2154
        bourgogne 2154
        lorraine 2154
        centre 2154
        nord-pas-de-calais 2154
        languedoc-roussillon 2154
        poitou-charentes 2154
        aquitaine 2154
        bretagne 2154
        ile-de-france 2154
        midi-pyrenees 2154
        provence-alpes-cote-d-azur 2154
        pays-de-la-loire 2154
        rhone-alpes 2154
EOT


    read full_list_keept_for_record << EOT2
        mayotte 32738
        guyane 2972
        corse 2154
        martinique 32620
        guadeloupe 32620
        reunion 2975
        limousin 2154
        champagne-ardenne 2154
        haute-normandie 2154
        franche-comte 2154
        basse-normandie 2154
        picardie 2154
        alsace 2154
        auvergne 2154
        bourgogne 2154
        lorraine 2154
        centre 2154
        nord-pas-de-calais 2154
        languedoc-roussillon 2154
        poitou-charentes 2154
        aquitaine 2154
        bretagne 2154
        ile-de-france 2154
        midi-pyrenees 2154
        provence-alpes-cote-d-azur 2154
        pays-de-la-loire 2154
        rhone-alpes 2154
EOT2

}

function download_pbfs {
    while read region projection ; do
        url="http://download.geofabrik.de/europe/france/${region}-latest.osm.pbf"
        filename=`basename $url`
        filepath="$DOWNLOAD_DIR/$filename"
        curl -s "$url" -o "$filepath"
        sleep 1
        echo $region $filepath $projection
    done
}


function predict {
    while read region pbf projection ; do
       result="$RESULT_DIR/segmented_building_predict-france_$region.bz2"
       echo "==========================================================>" 1>&2
       echo "| $region $projection" 1>&2
       echo "| $pbf => $result" 1>&2
       $PREDICT $pbf $projection | bzip2 > $result
       echo $result
       rm -f "$pbf"
    done
}

function post_osmose {
    while read result_xml ; do
        $OSMOSE_POST `cat $OSMOSE_CONF` $result_xml
    done
}

(cd "$SEGMENTED_DATA_DIR" && make -s 3)

echo "Start download..." 1>&2

if [ "$1" == "--osmose" ] ; then
    PREDICT=$PREDICT --osmose
    list_regions | download_pbfs | predict | post_osmose
else
    list_regions | download_pbfs | predict 
fi


