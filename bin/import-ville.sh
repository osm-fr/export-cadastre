#!/bin/bash
# ©Cléo 2010
# GPL v3 or higher — http://www.gnu.org/licenses/gpl-3.0.html
# $1 dep $2 code ville $3 nom de la ville

. ./config
cd $data_dir

Qadastre2OSM="$bin_dir/Qadastre2OSM"

[ -d $1 ] || mkdir $1
chmod 777 $1

cd $1
date
$Qadastre2OSM --download $1 $2 "$3"
$Qadastre2OSM --convert $2 "$3"
rm -f "$2-$3.tar.bz2"
tar cvf "$2-$3.tar" --exclude="*.pdf" --exclude="*-water.osm" $2-"$3"*
bzip2 -f "$2-$3.tar"
cd ..
# Création du dossier si celui-ci n'existe pas
mkdir eau 2>/dev/null
chmod 777 eau 
mv -f $1/*.pdf $1/*-water.osm eau
date
