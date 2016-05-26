
Import de addr:housenumber depuis le cadastre (http://cadastre.gouv.fr)

ATTENTION: l'utilisation des données du cadastre n'est pas libre, et ces
scripts doivent donc être utilisés exclusivement pour contribuer à
OpenStreetMap, voire 
http://wiki.openstreetmap.org/wiki/Cadastre_Fran%C3%A7ais/Conditions_d%27utilisation


Ce répertoire contient des scripts python utilisés pour importer 
les numéros de rue depuis le cadastre vers un fichier .osm 
(addr:housenumber OpenStreetMap).

Installation et Compilation
---------------------------
sudo apt-get install libpodofo-dev
sudo apt-get install qt4-qmake
sudo apt-get install libqt4-dev
sudo apt-get install python-gdal
sudo apt-get install python-numpy
sudo apt-get install python-sklearn
sudo apt-get install libspatialindex1
sudo pip install shapely
sudo pip install rtree
make

Le script principal:
--------------------

1. cadastre_vers_osm_adresses.py 

Tente d'importer à la fois les numéros et les noms de rues depuis le cadastre.
Récupère pour cela:
 - les exports pdf du cadastre, où seront repérés les numéros de rue, et les
   limites de parcelles
 - la liste des parcelles et les info les concernant, dont une liste 
   d'adresses.
Puis fuisionne ces deux sources de données en un seul fichier osm.
Le résultat est ensuite partitionné par rue pour les numéros dont
on a trouvé le nom de rue.

Script complémentaire:
----------------------
    https://github.com/vdct/associatedStreet

Utilisation:
------------

1. Récupération des adresses d'une commune depuis le cadastre:

    ./cadastre_vers_osm_adresses.py <code_département> <code_commune>

2. Décompresser le fichier zip obtenu:

    unzip <code_commune>-adresses.zip

3. Intégrer chacun des fichiers grâce à JOSM

    ATTENTION A FUSIONNER CORRECTEMENT LES DONNÉES OBTENUES ICI AVEC
    CELLES DEJA PRÉSENTES DANS OSM !
    IL NE FAUT PAS PAS IMPORTER DES ADRESSES QUI Y ETAIENT DÉJA !

    ATTENTION AUSSI A VÉRIFIER ET CORRIGER SI NECESSAIRE TOUS LES ELEMENTS
    AYANT UN TAG FIXME.

    Il est recommandé de commencer par intégrer les adresses correspondant
    aux rues avant d'intégrer les numéros <AMBIGUS> ou <ORPHELINS>

    pour chaque fichier .osm:
    - l'ouvrir dans JOSM
    - vérifier la cohérence des données (on ne sait jamais)
    - télécharger dans le même calque la zone correspondante de 
      OpenStreetMap
    - sélectionner la relation associatiedStreet du fichier original
    - ajouter et vérifier dans cette relation les highway associés
    - renomer la relation avec le vrai nom de la rue
    - intégrer les nœuds addr:housenumber a leur building si aproprié 
      (par exemple àvec la touche J pour intégrer le nœud à la bordure 
       du building) ou alors déplacer si nécéssaire le noeuds
      vers le point d'entré de la propriété associée.
    - passer en revue les numéros ayant un tag fixme, 
      puis suprimmer ce tag une fois l'incertitude levée ou le problème 
      éventuel corrigé. Dans un fichier ayant un nom de rue le fixme 
      peut correspondre:
        - a un numéros loin de la parcelle avec laquelle il a
          été automatiquement associé pour lui trouvé une rue, il faut
          donc s'assurer intuitivement que l'association de ce numéros
          à la rue semble correcte.
        - a un numéro associé à une parcelle mais dont la position
          exacte n'a pas été trouvé dessiné sur le cadastre.

   -  pour les fichiers <ORPHELINS> et <AMBIGUS>, il faut pour chaqun des 
      noeuds numéro qu'il contienne trouver à quelle rue les associer. 
      Le tag fixme poura être supprimé une fois fait.
      Attention les numéros peuvent en fait être des doublons, il peut déjà 
      y avoir un autre noeud addr:housenumber identique associé à la rue, 
      il faut alors choisr lequelle des deux est le mieux positionné 
      et fusionner l'autre avec lui (touche M).

    - Pour les fichiers <AMBIGUS>, le tag fixme listera chaque nom de rue
      pour lesquelles la parcelle associée au numéro avait une addresse. 
      Il faudra donc associé le numéro à la bonne rue avant de supprimer 
      le tag fixme.

    - Les fichiers <QUARTIERS> contienent des noeuds place=neighbourhood
      calculés automatiquement à partir d'adresses du cadastre sans numéro. 
      Il faut donc vérifier et surtout repositionné ces éléments avant
      de suprimer le tag fixme et de les intégrer a OpenStreetMap.


============================================================================
Simplification de bâtiments
---------------------------

Le script simplify_qadastre_houses.py sert a simplifier un fichier de 
bâtiments tel que le fichier CODE_COMMUNE-houses.osm obtenus par le programme
Qadastre.
Il vas:
 - fusioner les nœeuds proches
 - joindre les nœeuds aux segments proches
 - simplifier les chemins en supprimant des noeuds


============================================================================
Prédiction de bâtiments segmentés
---------------------------------

La prédiction de buildings potentiellement segmentés par le cadastre 
(le cadastre découpe les bâtiments aux limites de parcelles)
est le rôle du script segmented_building_predict.py

Ce script vas utiliser une Machine à Vecteurs de Support (SVM) sur
un vecteur composé de statistiques sur les angles formés par les 
segments du bâtiments pour intuiter si chaque couple de 
bâtiments contigue pourait être le résultat d'une segmentation 
due au cadasstre.

Les données d'apprentissage du classifier SVM sont présentes dans 
le répertoire segmented_building_data/
Ce répertoire contient des fichiers .osm où chaque bâtiments 
qui devraient être fusionés ensemble doivent avoir
un tag "joined" de valeur identique.
Le programme ./segmented_building_classifier.py génère le classifier 
à partir de tels fichiers .osm.

Le programme segmented_building_find_joined.py peux servir à générer
un fichier .osm à utiliser pour l'apprentissage en comparant deux fichiers
.osm (par exemple un extrait du cadastre, et un extrait d'OSM) et annote
le tag "joined" les bâtiments du premier fichier qui sont joints dans
le second.


============================================================================
Anciens scripts :
-----------------

2. cadastre_vers_osm_housenumbers.py 

Tente d'importer uniquement les nœuds addr:housumeber depuis le cadastre, mais 
sans aucune imformation conrernant les rues associées à ces numéros.


3. fusion_osm_highways_avec_housenumbers.py

Tente de fusionner les données obtenues depuis le serveur OpenStreetMap
avec un fichier osm contenant des addr:housenumber.
Il affecte au nœuds addr:housenumber un tag addr:street correspondant au
highway le plus proche, et il essaye aussi d'intégrer les nœuds 
addr:housenumber au building le plus proche.
ATTENTION ! dans un nombre considérable de cas, le choix de l'élément 
le plus proche n'est pas le bon choix, donc ce script se trompe
très très souvent et il faut absolument tout vérifier et corriger
manuellement derrière !



============================================================================
Le code de récupération des adresses:
-------------------------------------
Le code de récupération des pdf est un mix entre le code du programme
Qadastre de Pierre Ducroquet (https://gitorious.org/qadastre/qadastre2osm)
et du script import-bati.sh
(http://svn.openstreetmap.org/applications/utils/cadastre-france/import-bati.sh)

La récuparétaion des pdf est morcelée en plusieurs fichiers correspondant
chacun à une bbox de taille maximale 2000 afin d'avoir une bonne précision 
et être capable d'en extraire les numéros de rue (dessinés petit).

L'analyse des fichiers pdf a d'abord été faites a partir d'une version 
svg (voir pdf_vers_svg.py)
Maintenant le petit programme pdfparser fait l'équivalent, il génère
les path contenus dans le pdf avec une syntaxe équivalente à celle des
path svg.

La reconnaisance des caractères est basée sur une comparaison avec
les paths contenus dans les fichiers svg reference-*.svg
Les paths sont normalisés pour obtenir
 - une liste de commandes
 - une liste de coordonées absolues
Les cordonnées sont ensuite pivotées et mise à l'échèle pour être
comparées a celles des fichiers de référence.


