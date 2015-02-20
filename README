== git == 
Le projet cadastre est géré par git, c'est pourquoi j'ai fait des liens un peu à l'arrache comme ça.

== cron ==
Ligne à mettre dans le cron : (ça sert à purger nomber logs, et fichier qui
sont généré et finalement obsolètes)

0 3 * * * cd /data/project/cadastre.openstreetmap.fr/export-cadastre/bin/ ; ./maj-dep-massif.sh

== zone d'accès restreint aux export de polygones rivières ==
Dans le dossier des data, pensez à créer un dossier "eau" et le protéger par
un .htaccess avec le mot de passe indiqué dans
mot-de-passe-acces-a-cadastre-eau

== Qadastre2OSM ==
Ici se trouve une copie du code de Qadastre2OSM qui a été patché avec le
temps et qui s'est bien désynchronisée de l'original que l'on peut trouver à
: http://gitorious.org/qadastre/qadastre2osm

Une merge entre les dépots a été réalisé via un git subtree. Pour le créer, 
il faut executer les commandes suivantes :

  git remote add qadastre2osm git@gitorious.org:qadastre/qadastre2osm.git
  git pull -s subtree qadastre2osm master

Pour pusher des modifications, vers un fork de qadastre2osm :

  git remote add qadastre2osm_fork git@gitorious.org:qadastre/<NICKNAME>s-qadastre2osm.git
  git subtree push --prefix=bin/Qadastre2OSM-src/ qadastre2osm_fork master

Il suffit ensuite de proposer un pull-request à ~pinaraf (l'auteur de Qadastre2OSM) 
via l'interface de gitorious.
