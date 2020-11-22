#!/bin/bash

. `dirname $0`/../config || exit -1
umask 002

export MPLCONFIGDIR="$work_dir/tmp"

if [[ $# != 3 && $# != 4 ]] ; then
    echo "ERREUR: mauvais nombre d'arguments"
    exit -1
fi
code_departement=$1
code_commune=$2
nom_commune=$3
bis=$4

if [ ${#code_departement} != 3 ] ; then
    echo "ERREUR: le code département doit avoir 3 caractères"
    exit -1
fi
if [ ${#code_commune} != 5 ] ; then
    echo "ERREUR: le code commune doit avoir 5 caractères"
    exit -1
fi

#
# Déduit le code INSEE
#
if [ ${code_departement:0:1} == "0" ] ; then
    code_insee=${code_departement:1:2}${code_commune:2:3}
else
  if [ ${code_departement:2:1} != ${code_commune:2:1} ] ; then
    echo "ERREUR: le code commune ne correspond pas au code departement"
    exit -1
  fi
  code_insee=${code_departement:0:2}${code_commune:2:3}
fi


#
# Lance la génération des adresses:
#

depdir="$data_dir/$code_departement"
communedir="$hidden_dir/$code_departement/$code_commune"
if [ "$bis" = "false" ] ; then
  nobis="-nobis"
fi

command1="env LD_LIBRARY_PATH=/home/tyndare/.local/lib/ PYTHONPATH=/home/tyndare/.local/lib/python2.7/site-packages/ $PWD/cadastre_fr/bin/cadastre_2_osm_addresses.py $nobis $code_departement $code_commune"
command1dir="$communedir"

#command2="python addr_fantoir_building.py $code_insee $code_commune"
#command2dir=$PWD/cadastre_fr/associatedStreet

command3="$PWD/cadastre_fr/bin/osm_associatedStreet_remover.py"

file1="${depdir}/${code_commune}-${nom_commune}-adresses-associatedStreet_sans_batiment.zip"
file2="${depdir}/${code_commune}-${nom_commune}-adresses-associatedStreet_mix_en_facade_ou_isole.zip"
#file3="${depdir}/${code_commune}-${nom_commune}-adresses-associatedStreet_tag_sur_batiment.zip"
#file4="${depdir}/${code_commune}-${nom_commune}-adresses-associatedStreet_point_sur_batiment.zip"
file5="${depdir}/${code_commune}-${nom_commune}-adresses-lieux-dits.zip"
file6="${depdir}/${code_commune}-${nom_commune}-mots.zip"

mkdir -p $communedir
chmod -R a+rw $communedir 2>/dev/null
umask 0000
rm -f $communedir/*building*.osm
rm -f $communedir/*building*.osm.ok

cd $command1dir && $command1 || exit -1
mv "$communedir/${code_commune}-adresses.zip" "${file1}"
mv "$communedir/${code_commune}-adresses_buildings_proches.zip" "${file2}"
$command3 "${file1}" "${file1/associatedStreet/addrstreet}"
$command3 "${file2}" "${file2/associatedStreet/addrstreet}"
mv "$communedir/${code_commune}-lieux-dits.zip" "${file5}"
mv "$communedir/${code_commune}-mots.zip" "${file6}"

#cd $command2dir && $command2 || exit -1

#mv "$communedir/${code_commune}_adresse_tag_sur_batiment.zip" "${file3}"
#mv "$communedir/${code_commune}_adresse_point_sur_batiment.zip" "${file4}"
#$command3 "${file3}" "${file3/associatedStreet/addrstreet}"
#$command3 "${file4}" "${file4/associatedStreet/addrstreet}"


