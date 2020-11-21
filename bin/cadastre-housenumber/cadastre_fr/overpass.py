#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with it. If not, see <http://www.gnu.org/licenses/>.


import os
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import os.path

from .osm      import OsmParser
from .tools    import print_flush
from .tools    import open_cached


def open_osm_overpass(requete, cache_filename, metropole=False):
    if metropole:
        # oapi-fr.openstreetmap.fr n'a que la métropole, pas l'outre mer
        overvass_server = "http://overpass-api.de/api/interpreter?"
    else:
        overvass_server = "http://overpass-api.de/api/interpreter?"
    url = overvass_server + urllib.parse.urlencode({'data':requete})
    print_flush(urllib.parse.unquote(url))
    try:
        with open_cached(lambda: urllib.request.urlopen(url), cache_filename) as f:
            result = OsmParser().parse_stream(f)
    except Exception as ex:
        if metropole:
            print_flush("ERREUR: " + repr(ex))
            print_flush("Tentative depuis le serveur allemand:")
            result = open_osm_overpass(requete, cache_filename, False)
        else:
            raise ex
    return result

