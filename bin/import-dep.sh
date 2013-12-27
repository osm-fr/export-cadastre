#!/bin/bash
# ©Cléo 2010
# GPL v3 or higher — http://www.gnu.org/licenses/gpl-3.0.html

. ./config
cd $data_dir

Qadastre2OSM="$bin_dir/Qadastre2OSM"

[ -d $1 ] || mkdir $1
cd $1
$Qadastre2OSM --list $1 > $1-liste.txt
sed -i "s/\([^ ]*\) - \(.*\) (.*)/\1 \2/" $1-liste.txt
while read l 
	do
		code=`echo $l|cut -d' ' -f1`
		ville=`echo $l|sed "s/[^ ]* //"`
		$Qadastre2OSM --download $1 $code $ville
		$Qadastre2OSM --convert $code $ville
		rm -f "$code-$ville.tar.bz2"
		tar cvf "$code-$ville.tar" --exclude="*.pdf" $code-$ville*
		bzip2 -f "$code-$ville.tar"
	done < $1-liste.txt
cd ..
