#!/usr/bin/env python
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
Prend en entrée des fichiers osm contenant des bâtiments (buildings) avec
un tag "segmented" contenant des valeurs égales pour les buildings à fusionner,
ou rien ou "segmented"="no" pour ceux à ne pas fusioner,
et "segmented"="?" pour ceux pour lequel c'est ambigue.

De tels fichiers d'entrée peuvent être générés par le programme
segmented_building_find_joined.py

La sortie de ce programme est la gérération de deux fichiers
    scaler.pickle
    classifier.pickle
dump d'une instance de Scaler pour mettre à l'échelle les valeurs
et d'un classifier pour prédire à partir de ces valeurs
deux bâtiments fractionnés.

Les valeurs (features) d'un couple de bâtiment doivent être obtenus
en appelant la fonction
    fr_cadastre_segmented.get_classifier_vector(wkt1, wkt2)


Plusieurs classifiers ont été expérimentés.

 - KNeighborsClassifier
   meilleur équilibre entre nombre de correcte / faux négatifs / faux positifs.
   (peut être car on a beaucoup plus de données d'apperntissage négatives, il faudrait jouer sur les weight pour rééquilibrer)
   meilleurs résultats avec
    MinMaxScaler()
    KNeighborsClassifier(weights="distance", k = 8)
   La grid search cross validation donne k=4 mais en fait avec k=8 c'est bien mieux.


 - DecisionTreeClassifier
    peu de manqués (faux négatifs), mais beaucoup de faux positifs
    je ne sais pas utiliser Scaler améliore vraiment ou pas.

 - SVM
    peu de faux positifs, mais beaucoup de faux négatifs (manqués).
    meilleurs résultats avec:
        MinMaxScaler()
        SVC(kernel="rbf",C=500 ou plus, gamma=0.05)

 - SGDClassifier
    mauvais résultats

"""


import sys
import pickle
import os.path

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from cadastre_fr.osm        import OsmParser
from cadastre_fr.osm        import OsmWriter
from cadastre_fr.tools      import command_line_error
from cadastre_fr.tools      import open_zip_and_files_with_extension
from cadastre_fr.transform  import get_centered_metric_equirectangular_transformation_from_osm
from cadastre_fr.segmented  import compute_transformed_position_and_annotate
from cadastre_fr.segmented  import get_segmented_buildings_data
from cadastre_fr.segmented  import train_kneighbors
from cadastre_fr.segmented  import train_svm
from cadastre_fr.segmented  import train_tree
from cadastre_fr.segmented  import train_sgd

HELP_MESSAGE = "USAGE: {0} buildins-with-segmented-tag.osm".format(sys.argv[0])

def main(argv):
    osm_args = [f for f in argv[1:] if os.path.splitext(f)[1] in (".zip", ".osm")]
    other_args = [f for f in argv[1:] if os.path.splitext(f)[1] not in (".zip", ".osm")]
    if len(other_args) != 0:
        command_line_error(u"invalid argument: " + other_args[0], HELP_MESSAGE)
    if len(osm_args) == 0:
        command_line_error(u"not enough file.osm args", HELP_MESSAGE)

    all_data = []
    all_result = []

    for name, stream in open_zip_and_files_with_extension(osm_args, ".osm"):
        print "load " + name
        osm = OsmParser().parse_stream(stream)
        inputTransform, outputTransform = get_centered_metric_equirectangular_transformation_from_osm(osm)
        compute_transformed_position_and_annotate(osm, inputTransform)

        data, result = get_segmented_buildings_data(osm)

        print " ->", len(result), "cas", result.count(1), " positif"
        all_data.extend(data)
        all_result.extend(result)

    scaler, classifier = train_kneighbors(all_data, all_result)
    #scaler, classifier = train_svm(all_data, all_result)
    #scaler, classifier = train_tree(all_data, all_result)
    #scaler, classifier = train_sgd(all_data, all_result)
    with open("classifier.pickle", "w") as f:
        pickle.dump(classifier, f)
    with open("scaler.pickle", "w") as f:
        pickle.dump(scaler, f)

    #for positive_weight in 1,2,5:
    #    print "-------------------------------------------------------------"
    #    print "Train with scoring for positive segemented building weighted %d over non segmented ones" % positive_weight
    #    scaler, classifier = train(all_data, all_result, weighted_scoring([1,positive_weight]))
    #    with open("classifier_%d.txt" % positive_weight, "w") as f:
    #        f.write(str(classifier))
    #        f.write("\n")
    #    with open("classifier_%d.pickle" % positive_weight, "w") as f:
    #        pickle.dump(classifier, f)
    #    with open("scaler_%d.pickle" % positive_weight, "w") as f:
    #        pickle.dump(scaler, f)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

