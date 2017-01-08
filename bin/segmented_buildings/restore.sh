#/bin/bash

echo -n "Are you sure you want to restore and overwrite all the segmented data [YES/NO] ?"
read answer
if [ "$answer" == "YES" ] ; then
    pg_restore --format=directory -c -1  dump -d cadastre && echo "restored" || echo "failed"
else
    echo "canceled"
fi

