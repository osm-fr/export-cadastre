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

"""
Accès au site web du Cadastre (https://cadastre.gouv.fr)
Permet d'obtenir les export pdf ainsi que les informations sur les parcelles.

ATTENTION: l'utilisation des données du cadastre n'est pas libre, et ce script doit
donc être utilisé exclusivement pour contribuer à OpenStreetMap, voire
http://wiki.openstreetmap.org/wiki/Cadastre_Fran%C3%A7ais/Conditions_d%27utilisation

Ce script est inspiré du programme Qadastre de Pierre Ducroquet
(https://gitorious.org/qadastre/qadastre2osm/)
et du script import-bati.sh
(http://svn.openstreetmap.org/applications/utils/cadastre-france/import-bati.sh)

"""

import re
import sys
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import http.cookiejar
import os.path
import time


CADASTRE_TIMEOUT_SESSION_SECONDES = 5*60

MAP_PROJECTION_IGNF_VERS_EPSG_CODE = {
  # Metropole, Lambert 9 zones:
    "RGF93CC42" : "3942",
    "RGF93CC43" : "3943",
    "RGF93CC44" : "3944",
    "RGF93CC45" : "3945",
    "RGF93CC46" : "3946",
    "RGF93CC47" : "3947",
    "RGF93CC48" : "3948",
    "RGF93CC49" : "3949",
    "RGF93CC50" : "3950",
  # Guadeloupe
    "GUAD48UTM20" : "2970",
    "GUADFM49U20" : "2969",
    "UTM20W84GUAD" : "4559",
  # Martinique
    "MART38UTM20" : "2973",
    "UTM20W84MART" : "4559",
  # Guyane
    "CSG67UTM21" : "3312",
    "CSG67UTM22" : "2971",
    "UTM22RGFG95" : "2972",
  # Réunion
    "REUN47GAUSSL" : "3727",
    "RGR92UTM40S" : "2975",
  # Mayotte
    "MAYO50UTM38S" : "2980",
    "CAD97UTM38S" : "4474",
    "RGM04UTM38S" : "4471",
  # St-Pierre et Miquelon
    "SPM50UTM21" : "2987",
    "RGSPM06U21" : "4467"
}

CORRECTIONS_PROJECTION_CADASTRE = {
    # Corrections de projections extraites de
    # https://github.com/osm-fr/export-cadastre/blob/master/bin/Qadastre2OSM-src/osmgenerator.cpp
    "RGFG95UTM22" : "UTM22RGFG95",
    "RGR92UTM" : "RGR92UTM40S",
    # Addition pour Mayotte:
    "RGM04" : "RGM04UTM38S",
}

CORRECTIONS_PROJECTION_CADASTRE_COMMUNE = {
    # Corrections de projections pour les îles Saint-Martin et Saint Barthélémy
    # le site cadastre.gouv.fr ne semble pas renvoyer la bonne valeur
    # voir https://lists.openstreetmap.org/pipermail/dev-fr/2010-November/000059.html
    "SAINT MARTIN (97150)" : "GUADFM49U20",
    "SAINT BARTHELEMY (ILE) (97133)" : "GUADFM49U20",
}


class CadastreWebsite(object):
  """Accèss au site web https://cadastre.gouv.fr"""

  def __init__(self):
    self.code_departement = None
    self.code_commune = None
    self.reinit_session()

  def reinit_session(self):
    self.session_start_time = time.time()
    # Crée un cookiejar pour maintenir le nouveau sessionid
    self.url_opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    # Récupération de la liste des départements
    self.departements = self.__parse_departements_list(
        self.url_opener.open(
            "https://www.cadastre.gouv.fr/scpc/rechercherPlan.do").read())
    code_departement = self.code_departement
    code_commune = self.code_commune
    self.code_departement = None
    self.code_commune = None
    self.communes = {}
    self.projection = None
    self.bbox = None
    if code_departement != None:
        self.set_departement(code_departement)
    if code_commune != None:
        self.set_commune(code_commune)

  def check_session_timeout(self):
    if time.time() > (self.session_start_time +
        CADASTRE_TIMEOUT_SESSION_SECONDES):
      sys.stderr.write("Réinitialise la connexion avec le site du cadastre.\n")
      sys.stderr.flush()
      self.reinit_session()

  def __parse_departements_list(self, html):
    resultat = {}
    html = html.decode("utf8")
    csrf_token_index = html.find("CSRF_TOKEN=")
    if csrf_token_index >= 0:
        csrf_token_index  = csrf_token_index + len("CSRF_TOKEN=")
        end_index = csrf_token_index
        while html[end_index] not in ('"', '&', "'", " "):
            end_index = end_index + 1
        self.CSRF_TOKEN = html[csrf_token_index:end_index]
    else:
        self.CSRF_TOKEN = ""
    html = html.split("<select name=\"codeDepartement\"")[1].split("</select>")[0]
    pattern = re.compile("<option value=\"(...)\">([^<]*)</option>", re.S)
    for match in pattern.finditer(html):
      code_departement = match.group(1)
      nom_departement = match.group(2).replace("&#39;","'")
      resultat[code_departement] = nom_departement
    return resultat

  def get_departements(self): return self.departements

  def get_communes(self):
    """retourne la liste des communes du département courant """
    return self.communes

  def get_projection(self):
    """retourne la projection de la commune courante """
    return self.projection

  def get_bbox(self):
    """retourne la bbox de la commune courante """
    return self.bbox

  def set_departement(self, code_departement):
    if self.code_departement == code_departement:
      return
    self.code_departement = None
    self.code_commune = None
    self.projection = None
    self.bbox = None
    communes = {}
    self.check_session_timeout()
    url = "https://www.cadastre.gouv.fr/scpc/listerCommune.do?CSRF_TOKEN=" + self.CSRF_TOKEN + "&codeDepartement=" \
        + code_departement \
        + "&libelle=&keepVolatileSession=&offset=5000"
    html = self.url_opener.open(url).read().decode("utf8")
    table_pattern = re.compile("<table[^>]*class=\"resonglet\"[^>]*>(.*?)</table>", re.S)
    # On ne considère que les communes vectorielles 'VECT':
    code_pattern = re.compile("ajoutArticle\\('([^']*)','VECT',", re.S);
    nom_pattern = re.compile("<strong>([^<]*)</strong>", re.S)
    for table_match in table_pattern.finditer(html):
      table_content = table_match.group(1)
      nom_match = nom_pattern.search(table_content)
      code_match = code_pattern.search(table_content)
      if (nom_match and code_match):
          code_commune = code_match.group(1)
          nom_commune = nom_match.group(1).strip()
          communes[code_commune] = nom_commune
    self.communes = communes
    self.code_departement = code_departement

  def set_commune(self, code_commune):
    if code_commune == self.code_commune:
      return
    self.code_commune = None
    self.projection = None
    self.bbox = None
    self.check_session_timeout()
    self.code_commune = code_commune
    url = self.__get_commune_url()
    html = self.url_opener.open(url).read()
    try:
        html = html.decode("utf8")
    except:
        html = html.decode("8859")
    bbox_pattern = re.compile(
        "new GeoBox\\(\\s*([0-9.]*),\\s*([0-9.]*),\\s*([0-9.]*),\\s*([0-9.]*)\\),\\s*\"([^\"]*)\",",
        re.S);
    bbox_match = bbox_pattern.search(html)
    self.projection = bbox_match.group(5)
    #print ("projection = " + self.projection)
    if self.projection in CORRECTIONS_PROJECTION_CADASTRE:
        print(("projection du cadastre corrigée de " + self.projection +
            " vers " + CORRECTIONS_PROJECTION_CADASTRE[self.projection]))
        self.projection = CORRECTIONS_PROJECTION_CADASTRE[self.projection]
    nom_commune = self.communes[self.code_commune]
    if nom_commune in CORRECTIONS_PROJECTION_CADASTRE_COMMUNE:
        print(("projection du cadastre corrigée de " + self.projection +
            " vers " + CORRECTIONS_PROJECTION_CADASTRE_COMMUNE[nom_commune]))
        self.projection = CORRECTIONS_PROJECTION_CADASTRE_COMMUNE[nom_commune]
    x1 = float(bbox_match.group(1))
    y1 = float(bbox_match.group(2))
    x2 = float(bbox_match.group(3))
    y2 = float(bbox_match.group(4))
    self.bbox =  (x1,y1,x2,y2)


  def open_pdf(self, bbox, width, height):
    """ ouvre l'export pdf de la commune courante, pour la bbox donnée,
        avec la taille donnée """
    self.check_session_timeout()
    post_data = {
        #k.encode("utf8"):v.encode("utf8") for (k,v) in {
          "WIDTH" : "%d" % width,
          "HEIGHT" : "%d" % height,
          "MAPBBOX" : "%f,%f,%f,%f" % bbox,
          "SLD_BODY" : "",
          "RFV_REF" : self.code_commune
        #}.items()
    }
    url = "https://www.cadastre.gouv.fr/scpc/imprimerExtraitCadastralNonNormalise.do?CSRF_TOKEN=" + self.CSRF_TOKEN
    return self.url_opener.open(url, urllib.parse.urlencode(post_data).encode("utf8"))

  def get_parcel_lon_lat(self, lon, lat):
    return self.get_parcel(lon, lat, epsg="4326")

  def get_parcel(self, x, y, epsg=None):
    """ retourne l'id de la parcelle situé au coordonées données
        (exprimées dans la projection epsg donnée ou à défaut celle
         de la commune courante)"""
    self.check_session_timeout()
    if epsg==None:
      epsg = MAP_PROJECTION_IGNF_VERS_EPSG_CODE[self.projection]
    data = '<?xml version="1.0" encoding="UTF-8"?>' + \
        '<wfs:GetFeature service="WFS" version="1.0.0"' + \
        ' outputFormat="XML-alcer" xmlns:topp="http://www.openplans.org/topp"' + \
        ' xmlns:wfs="http://www.opengis.net/wfs"' + \
        ' xmlns:ogc="http://www.opengis.net/ogc"' + \
        ' xmlns:gml="http://www.opengis.net/gml"' + \
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' + \
        ' xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.0.0/WFS-basic.xsd"' + \
        ' maxFeatures="2000">' + \
          '<wfs:Query typeName="CDIF:PARCELLE">' + \
            '<ogc:Filter>' + \
              '<ogc:And>' + \
                '<ogc:PropertyIsEqualTo>' + \
                  '<ogc:PropertyName>COMMUNE_IDENT</ogc:PropertyName>' + \
                  '<ogc:Literal>' + self.code_commune + '</ogc:Literal>' + \
                '</ogc:PropertyIsEqualTo>' + \
                '<ogc:Intersects>' + \
                  '<ogc:PropertyName>GEOM</ogc:PropertyName>' + \
                  '<gml:MultiPoint srsName="http://www.opengis.net/gml/srs/epsg.xml#' + epsg + '">' + \
                    '<gml:PointMember>' + \
                      '<gml:Point>' + \
                        '<gml:coordinates>' + str(x) + "," + str(y) + '</gml:coordinates>' + \
                      '</gml:Point>' + \
                    '</gml:PointMember>' + \
                  '</gml:MultiPoint>' + \
                '</ogc:Intersects>' + \
              '</ogc:And>' + \
            '</ogc:Filter>' + \
          '</wfs:Query>' + \
        '</wfs:GetFeature>'
    url = "https://www.cadastre.gouv.fr/scpc/wfs"
    request = urllib.request.Request(url)
    request.add_data(data)
    request.add_header('content-type', 'application/xml; charset=UTF-8')
    request.add_header('referer', self.__get_commune_url())
    answer = self.url_opener.open(request).read().decode("utf8")
    #print answer
    parcel_search = re.search('<PARCELLE fid="PARCELLE\\.([A-Z0-9]+)">', answer)
    if parcel_search:
      return parcel_search.group(1)
    else:
      return None

  def open_parcels_xml(self, x1, y1, x2, y2, epsg=None):
    self.check_session_timeout()
    """ retourne la description des parcelles situé dans la bbox données
        (exprimées dans la projection epsg donnée ou à défaut celle de la
        commune courrante)"""
    if epsg==None:
      epsg = MAP_PROJECTION_IGNF_VERS_EPSG_CODE[self.projection]
    data = '<?xml version="1.0" encoding="UTF-8"?>' + \
        '<wfs:GetFeature service="WFS" version="1.0.0"' + \
        ' outputFormat="XML-alcer" xmlns:topp="http://www.openplans.org/topp"' + \
        ' xmlns:wfs="http://www.opengis.net/wfs"' + \
        ' xmlns:ogc="http://www.opengis.net/ogc"' + \
        ' xmlns:gml="http://www.opengis.net/gml"' + \
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' + \
        ' xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.0.0/WFS-basic.xsd"' + \
        ' maxFeatures="2000">' + \
          '<wfs:Query typeName="CDIF:PARCELLE">' + \
            '<ogc:Filter>' + \
              '<ogc:And>' + \
                '<ogc:PropertyIsEqualTo>' + \
                  '<ogc:PropertyName>COMMUNE_IDENT</ogc:PropertyName>' + \
                  '<ogc:Literal>' + self.code_commune + '</ogc:Literal>' + \
                '</ogc:PropertyIsEqualTo>' + \
                '<ogc:Intersects>' + \
                  '<ogc:PropertyName>GEOM</ogc:PropertyName>' + \
                  '<gml:Box srsName="http://www.opengis.net/gml/srs/epsg.xml#' + epsg + '">' + \
                    '<gml:coordinates>' + \
                      str(x1) + "," + str(y1) + ' ' + \
                      str(x2) + "," + str(y2) + \
                    '</gml:coordinates>' + \
                  '</gml:Box>' + \
                '</ogc:Intersects>' + \
              '</ogc:And>' + \
            '</ogc:Filter>' + \
          '</wfs:Query>' + \
        '</wfs:GetFeature>'
    url = "https://www.cadastre.gouv.fr/scpc/wfs"
    request = urllib.request.Request(url)
    request.add_data(data)
    request.add_header('content-type', 'application/xml; charset=UTF-8')
    request.add_header('referer', self.__get_commune_url())
    answer = self.url_opener.open(request)
    return answer

  def get_parcel_info(self, parcel):
    """retourne les infos de la parcelle"""
    data = "<PARCELLES><PARCELLE>" + parcel + "</PARCELLE></PARCELLES>"
    url = "https://www.cadastre.gouv.fr/scpc/afficherInfosParcelles.do?CSRF_TOKEN=" + self.CSRF_TOKEN
    request = urllib.request.Request(url)
    request.add_data(data)
    request.add_header('content-type', 'application/xml; charset=UTF-8')
    request.add_header('referer', self.__get_commune_url())
    answer = self.url_opener.open(request).read() # not utf-8
    return answer.decode("latin1")

  def get_parcel_address(self, parcel):
    """ retourne une liste d'adresse de la parcelle"""
    info = self.get_parcel_info(parcel)
    result = []
    for strong_group in info.split("<strong>"):
      address_end = re.search("</strong>\s*Adresse de la parcelle", strong_group)
      if address_end:
        result.append("\n".join(map(str.strip, strong_group[:address_end.start()].split("<br>"))))
    return result

  def __get_commune_url(self):
      return 'https://www.cadastre.gouv.fr/scpc/afficherCarteCommune.do?CSRF_TOKEN=' + self.CSRF_TOKEN \
          + '&c=' + self.code_commune + '&dontSaveLastForward&keepVolatileSession='

  def open_parcels_infos_pdf(self, parcels):
    """ouvre le pdf qui contient les infos des parcelles données"""
    self.check_session_timeout()
    data = "<PARCELLES><PARCELLE>" + "</PARCELLE><PARCELLE>".join(parcels) + "</PARCELLE></PARCELLES>"
    url = "https://www.cadastre.gouv.fr/scpc/afficherInfosParcelles.do?CSRF_TOKEN=" + self.CSRF_TOKEN
    request = urllib.request.Request(url)
    request.add_data(data)
    request.add_header('content-type', 'application/xml; charset=UTF-8')
    request.add_header('referer', self.__get_commune_url())
    answer = self.url_opener.open(request).read()
    # Quand on demande les infos de plusieurs parcelles, il faut ensuite
    # ouvrir le pdf pour avoir les infos:
    url = "https://www.cadastre.gouv.fr/scpc/editerInfosParcelles.do?CSRF_TOKEN=" + self.CSRF_TOKEN
    request = urllib.request.Request(url)
    request.add_header('referer', self.__get_commune_url())
    return self.url_opener.open(request)



def command_line_open_cadastre_website(argv):
  """Ouvre le cadastre pour le département argv[1] et la commune argv[2]
     retourne soit l'instnace de CadastreWebsite ouverte, soit
     un message d'erreur sous forme de chaine de caractère
  """
  if len(argv) <= 1:
      # Liste les départements
      departements = CadastreWebsite().get_departements();
      code_departements = list(departements.keys())
      code_departements.sort()
      for code in code_departements:
          sys.stdout.write("%s : %s\n" % (code, departements[code]))
  else:
      code_departement = argv[1]
      cadastreWebsite = CadastreWebsite()
      departements = cadastreWebsite.get_departements()
      if not (code_departement in departements):
          if ("0" + code_departement) in departements:
              code_departement = "0" + code_departement
          else:
              # cherche le département par son nom
              recherche = code_departement.upper()
              departements_possibles = [code for code,nom in list(departements.items())
                  if nom.upper().find(recherche) >= 0]
              if len(departements_possibles) == 0:
                  return "département invalide: " + code_departement
              elif len(departements_possibles) > 1:
                  return "département imprécis: " + code_departement
              else:
                  code_departement=departements_possibles[0]
      cadastreWebsite.set_departement(code_departement)
      communes = cadastreWebsite.get_communes()
      if (len(argv) == 2):
          # Liste les communes (triées par nom)
          communes = [(nom,code) for (code,nom) in list(communes.items())]
          communes.sort()
          for nom,code in communes:
              sys.stdout.write("%s : %s\n" % (code, nom))
      else:
          code_commune = argv[2]
          if not (code_commune in communes):
              # cherche de la commune par son nom
              recherche = code_commune.upper()
              communes_possibles = [code for code,nom in list(communes.items())
                  if nom.upper().find(recherche) >= 0]
              if len(communes_possibles) == 0:
                  return "commune invalide: " + code_commune
              elif len(communes_possibles) > 1:
                  for code in communes_possibles:
                      sys.stdout.write("%s : %s\n" % (code, communes[code]))
                  return "commune imprécise: " + code_commune
              else:
                  code_commune=communes_possibles[0]
          nom_commune = communes[code_commune]
          cadastreWebsite.set_commune(code_commune)
          return cadastreWebsite


def code_insee(code_departement, code_commune):
  """Déduit le code insee (5 caractères) d'une commune à partir des codes
     issus du cadastre: départememt (3 caractères) et commune (5 caractères)
  """
  assert(len(code_departement) == 3)
  assert(len(code_commune) == 5)
  if code_departement[0] == "0":
      result = code_departement[1:] + code_commune[2:]
  else:
      assert(code_departement[2] == code_commune[2])
      result = code_departement[:2] + code_commune[2:]
  return result





#######################################################$$

def test_cadastre():
    print("test_cadastre")
    cadastre = CadastreWebsite()
    list_dep = cadastre.get_departements()
    assert(list_dep["081"] == "81 - TARN")
    cadastre.set_departement("081")
    communes = cadastre.get_communes()
    code_commune = [code for code in list(communes.keys()) if code.endswith("020")][0]
    assert(communes[code_commune] == "AUSSAC (81600)")
    cadastre.set_commune(code_commune)
    pdf_file = cadastre.open_pdf(cadastre.get_bbox(), 100, 100)
    pdf_data = pdf_file.read(4)
    pdf_file.close()
    assert(pdf_data[0:4] == "%PDF")
    assert(cadastre.get_parcel_lon_lat("2.0307573", "43.8645129") == "UK0200000A1149")
    assert(cadastre.get_parcel("1621947.6513530577","3185210.5969969486", "3944") == "UK0200000A1267")

if __name__ == '__main__':
    test_cadastre()

