#!/bin/bash
# ©Cléo 2010
# GPL v3 or higher — http://www.gnu.org/licenses/gpl-3.0.html
# $1 dep $2 code ville $3 nom de la ville

cd /data/project/cadastre.openstreetmap.fr/data

[ -d $1 ] || mkdir $1
cd $1
date
echo /data/project/cadastre.openstreetmap.fr//bin/Qadastre2OSM --download $1 $2 "$3"
/data/project/cadastre.openstreetmap.fr//bin/Qadastre2OSM --download $1 $2 "$3"
echo /data/project/cadastre.openstreetmap.fr//bin/Qadastre2OSM --convert $2 "$3"
/data/project/cadastre.openstreetmap.fr//bin/Qadastre2OSM --convert $2 "$3"
rm -f "$2-$3.tar.bz2"
tar cvf "$2-$3.tar" --exclude="*.pdf" --exclude="*-water.osm" $2-"$3"*
bzip2 -f "$2-$3.tar"
cd ..
mv $1/*.pdf $1/*-water.osm eau
date
