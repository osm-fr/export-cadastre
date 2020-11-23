

# Récupére la liste des id relation délimititants les communes
# depuis leur code INSEE.

FILENAME=osm_id_ref_insee.csv

OVERPASS_URL=https://overpass-api.de/api/interpreter?data=

REQUEST=[out:csv(::"id","ref:INSEE";true;",")];relation["ref:INSEE"]["type"="boundary"]["admin_level"="8"];out;

URL_QUOTE=python3 -c "import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.readline()))"

OVERPASS_REQUEST="$(OVERPASS_URL)`echo '$(REQUEST)' | $(URL_QUOTE)`"


all:
	# Remove .ok if older than 15 days:
	find . -name $(FILENAME).ok -mtime +15 -exec rm {} \;
	make $(FILENAME).ok

$(FILENAME).ok:
	wget "$(OVERPASS_REQUEST)" -O $(FILENAME).tmp
	# remove result file smaller thant 300K
	find . -name $(FILENAME).tmp -size -300k -exec rm {} \;
	mv -f $(FILENAME).tmp $(FILENAME)
	touch $(FILENAME).ok


clean distclean:
	rm -f $(FILENAME) $(FILENAME).ok $(FILENAME).tmp
