#!/bin/bash
# ©Cléo 2010
# GPL v3 or higher — http://www.gnu.org/licenses/gpl-3.0.html
# $1 dep $2 code ville $3 nom de la ville $4 bbox optionnelle

dep="$1"
code="$2"
name="$3"
bbox="$4"

. `dirname $0`/config
cd $data_dir || exit -1

Qadastre2OSM="$bin_dir/Qadastre2OSM"
cadastre_vers_pdf="$bin_dir/cadastre-housenumber/cadastre_vers_pdf.py"
simplify_qadastre_houses="env LD_LIBRARY_PATH=/home/tyndare/.local/lib/ PYTHONPATH=/home/tyndare/.local/lib/python2.7/site-packages/ $bin_dir/cadastre-housenumber/simplify_qadastre_houses.py"


[ -d $dep ] || mkdir $dep
chmod 777 $dep

cd $dep
date


if [ "$bbox" = "" ] ; then
  # Téléchargement original:
  $Qadastre2OSM --download $dep $code "$name"
else
  # Téléchargement alternatif, qui nxtrait seulement une zone (bbox)
  name=$name-extrait-`date +"%Y-%m-%d_%Hh%Mm%Ss"`
  $cadastre_vers_pdf -bbox "$bbox" -nb 1 -wait 0 $dep $code
  # renomme les fichiers générés:
  rm -f $code-*.txt
  rm -f $code-*.ok
  rm -f "$code.bbox"
  mv -f "$code-0-0.bbox" "$code-$name.bbox"
  mv -f "$code-0-0.pdf" "$code-$name.pdf"
fi


$Qadastre2OSM --convert $code "$name"

$simplify_qadastre_houses "$code-$name-houses.osm"

rm -f "$code-$name.tar.bz2"
tar cvf "$code-$name.tar" --exclude="*-water.osm" $code-"$name"*.osm
bzip2 -f "$code-$name.tar"
cd ..
# Création du dossier si celui-ci n'existe pas
mkdir eau 2>/dev/null
chmod 777 eau 
mv -f $dep/*.pdf $dep/*-water.osm eau
date
