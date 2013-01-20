#!/bin/bash
# ©Cléo 2010
# GPL v3 or higher — http://www.gnu.org/licenses/gpl-3.0.html

temp_file=/dev/shm/tempo.txt
. ./config
cd $data_dir

Qadastre2OSM="$bin_dir/Qadastre2OSM"

rm eau/*
for i in 976 975 974 973 972 971 007 029 035 041 045 052 053 056 068 070 072 088 089 090 002 014 027 050 051 054 055 057 060 061 067 075 077 078 091 092 093 094 095 008 059 062 076 080 02A 02B 009 011 017 034 064 065 066 083 004 006 012 013 030 032 040 047 048 081 082 084 005 007 015 019 024 026 033 038 043 046 073 001 003 016 017 023 042 063 069 074 087  018 021 025 036 037 039 044 049 058 071 031 070 090 091 034 079 085 086 010 022 028 
do
	[ -d $i ] || mkdir $i
	cd $i
	#Parfois, Qadastre2OSM plante et ce fichier est vidé, on va le garder de coté et le reprendre si l'autre est vide
	mv *-liste.txt $temp_file

	# Ajouter par sly (sylvain@letuffe.org) pour éviter que des gens se retrouvent avec une trop vielle version des fichiers à importer
	rm *
	$Qadastre2OSM --list $i > $i-liste.txt

	# Fichier vide, plantage probable, on reprend notre sauvegarde
	if ! test -s $i-liste.txt ; then
		cp $temp_file $i-liste.txt
	fi
	rm $temp_file
	
	cd ..
done
