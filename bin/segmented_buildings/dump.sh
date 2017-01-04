#/bin/bash


pg_dump --table "segmented_*" --format directory -f dump cadastre
