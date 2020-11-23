#!/bin/bash
# ©Cléo 2010
# GPL v3 or higher — http://www.gnu.org/licenses/gpl-3.0.html

. `dirname $0`/../config || exit -1
cd $data_dir || exit -1

umask 002

echo "Nettoyage des données"
test -d "$water_dir"  && rm -rf "$water_dir"/* 2>/dev/null
test -d "$log_dir"    && rm -rf "$log_dir"/* 2>/dev/null
test -d "$hidden_dir" && rm -rf "$hidden_dir"/* 2>/dev/null
test -d "$lock_dir"   && rm -rf "$lock_dir"/* 2>/dev/null

# rm */* dans $data pour garder les fichier de liste de communes
# à la racine au cas où leur récupération échoue:
test -d "$data_dir"   && find "$data_dir" -type f \
    \! \( -name "*-liste.txt" -or -name ".htpasswd" -or -name ".htaccess" \) \
    -exec rm -rf {} \
    2>/dev/null

# Mise à jour Fantoir:
make -C $bin_dir/cadastre_fr/data/fantoir
# Mise à jour code insee
make -C $bin_dir/cadastre_fr/data/osm_id_ref_insee

echo "Récupération de la liste de départements et des communes…"
cd "$data_dir" && "$bin_dir/cadastre_fr/bin/cadastre_liste.py"

