#!/bin/bash
# GPL v3 or higher — http://www.gnu.org/licenses/gpl-3.0.html
# $1 dep $2 code ville $3 nom de la ville $4 bbox optionnelle

# Split cadastre pdf export in 200m x 200x square to avoid precision issues.

if [ $# -lt 3 ]; then
  echo -e "$0 department insee name [bbox(lon1,lat1,lon2,lat2)]\nEx: $0 02A AA142 LEVIE\nEx2: $0 02A AA142 LEVIE 9.12206,41.70100,9.12627,41.69932"
  exit 1
fi
dep="$1"
code="$2"
name="$3"
bbox="$4"

. `dirname $0`/config
cd $data_dir || exit -1
export MPLCONFIGDIR="$work_dir/tmp"

Qadastre2OSM="$bin_dir/Qadastre2OSM"
cadastre_2_pdf="env LD_LIBRARY_PATH=/home/tyndare/.local/lib/ PYTHONPATH=/home/tyndare/.local/lib/python2.7/site-packages/ $bin_dir/cadastre-housenumber/bin/cadastre_2_pdf.py"
osm_houses_simplify="env LD_LIBRARY_PATH=/home/tyndare/.local/lib/ PYTHONPATH=/home/tyndare/.local/lib/python2.7/site-packages/ $bin_dir/cadastre-housenumber/bin/osm_houses_simplify.py"
pdf_2_osm_houses="env LD_LIBRARY_PATH=/home/tyndare/.local/lib/ PYTHONPATH=/home/tyndare/.local/lib/python2.7/site-packages/ $bin_dir/cadastre-housenumber/bin/pdf_2_osm_houses.py "
segmented_building_predict="env LD_LIBRARY_PATH=/home/tyndare/.local/lib/ PYTHONPATH=/home/tyndare/.local/lib/python2.7/site-packages/ $bin_dir/cadastre-housenumber/bin/osm_segmented_building_predict.py"

[ -d $dep ] || mkdir $dep
chmod 777 $dep

dest_dir="$data_dir/$dep"
download_dir="$hidden_dir/$dep/$code"
water_dir="$data_dir/eau/"
mkdir -m 777 -p $download_dir
chmod 777 $hidden_dir
chmod 777 $hidden_dir/$dep

if [ "$bbox" = "" ] ; then
  bboxargs=""
else
  bboxargs="-bbox $bbox"
  time=`date +"%Y-%m-%d_%Hh%Mm%Ss"`
  name=$name-extrait-$time
  download_dir="$download_dir/$time"
  mkdir -p -m 777 $download_dir
fi


rm -f "dest_dir/$code-$name.tar.bz2"
mkdir $water_dir 2>/dev/null
chmod 777 $water_dir 2>/dev/null
cd $download_dir || exit -1
chmod 777 $download_dir 2>/dev/null

city_limit_top_size=0

$cadastre_2_pdf $bboxargs -size 200 $dep $code | while read pdf; do
  echo $pdf
  basename=`basename "$pdf" .pdf`
  index=`echo "$basename" |cut -c 7-`
  
  $($Qadastre2OSM --convert $code "$index" > /dev/null 2>&1)
  #mv -f *-water.osm $water_dir/ > /dev/null 2>&1
  
  #city_limit_size=`stat -c%s "$code-$index-city-limit.osm" 2> /dev/null || echo 0` 
  #if [ "$city_limit_size" -gt "$city_limit_top_size" ] ; then
  #  city_limit_top_size="$city_limit_size"
  #  mv -f "$code-$index-city-limit.osm" "$dest_dir/$code-$name-city-limit.osm"
  #else
  #  rm -f "$code-$index-city-limit.osm"
  #fi

  if [ -f "$code-$index-cemeteries.osm" ] ; then
    mv -f "$code-$index-cemeteries.osm" "$dest_dir/$code-$name-$index-cemeteries.osm"
  fi
  if [ -f "$code-$index-rails.osm" ] ; then
    mv -f "$code-$index-rails.osm" "$dest_dir/$code-$name-$index-rails.osm"
  fi
  
done

$pdf_2_osm_houses $code
mv $code-houses.osm "$dest_dir/$code-$name-houses.osm"
mv $code-city-limit.osm "$dest_dir/$code-$name-city-limit.osm"
mv $code-water.osm "$water_dir/$code-$name-water.osm"
cd "$dest_dir" && $osm_houses_simplify "$code-$name-houses.osm"
cd "$dest_dir" && $segmented_building_predict "$code-$name-houses-simplifie.osm" "$code-$name-houses-prediction_segmente.osm"
cd "$dest_dir" && tar jcf "$code-$name.tar.bz2" --exclude="*-water.osm" $code-"$name"*.osm

if [ "$bbox" != "" ] ; then
  rm -rf "$download_dir"
fi

