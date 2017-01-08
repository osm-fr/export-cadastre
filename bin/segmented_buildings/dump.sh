#/bin/bash


mv -f dump dump.old
pg_dump --table "segmented_*" --format directory -f dump cadastre  && rm -rf dump.old || mv -f dump.old dump
