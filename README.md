
# Export du cadastre français vers des données au format OpenStreetMap

Projet historique pour exporter des données du cadastre depuis le site web
	https://cadastre.gouv.fr
en analysant les PDF générés.


## Dépendances

Pour s'exécuter:

 * apache2 php libapache2-mod-php
 * python3 python3-rtree python3-shapely python3-gdal python3-distutils python3-sklearn
 * wget

Pour construire les exécutables:

 * g++ make python3-dev qt4-qmake libpodofo-dev libqt4-dev libproj-dev libgeos++-dev zlib1g-dev libjpeg-dev



## Installation:

## Git
    git clone --recurse-submodules git@github.com:osm-fr/export-cadastre.git


### work directory

    Vous pouvez créer un lien symbolique nommé "work" à la racine
    vers un répertoire où seront stockées les données de travail.


### www-data group

    L'utilisateur lancant les commandes doit appartenir au groupe "www-data" du serveur appache.

### make

    Lancer la commande
        make
    Cela vas :
        - cérer un fichier 'config',
        - initialiser le contenu du réperoire "work"
        - builder les exécutables
        - initialiser la liste des villes de chaque département

### Appache configuration


Configurer un VirtualHost Appache avec
    <VirtualHost …>
        …
        DocumentRoot <installation directory>/export-cadastre/web
        …
    </VirtualHost>
    <Directory <installation directory>/export-cadastre/web>
    	Options Indexes FollowSymLinks
	    AllowOverride None
	    Require all granted
    </Directory>


### cron

Ligne à mettre dans le cron : (ça sert à purger nomber logs, et fichier qui
sont généré et finalement obsolètes)
```
0 3 * * * cd <instalation directory>/export-cadastre/bin/ ; ./maj-dep-massif.sh
```


## Sous projets

Plusieurs sous projets historiques sont utilisés:

### Qadastre2OSM

Ici se trouve une copie du code de Qadastre2OSM qui a été patché avec le
temps et qui s'est bien désynchronisée de l'original que l'on peut trouver à : http://gitorious.org/qadastre/qadastre2osm

Une merge entre les dépots a été réalisé via un git subtree. Pour le créer,
il faut executer les commandes suivantes :
```
  git remote add qadastre2osm git@gitorious.org:qadastre/qadastre2osm.git
  git pull -s subtree qadastre2osm master
```
Pour pusher des modifications, vers un fork de qadastre2osm :
```
  git remote add qadastre2osm_fork git@gitorious.org:qadastre/<NICKNAME>s-qadastre2osm.git
  git subtree push --prefix=bin/Qadastre2OSM-src/ qadastre2osm_fork master
```
Il suffit ensuite de proposer un pull-request à ~pinaraf (l'auteur de Qadastre2OSM)
via l'interface de gitorious.
