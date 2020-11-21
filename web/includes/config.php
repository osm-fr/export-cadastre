<?php
//$temporary_dir = "/home/osm/export-cadastre/";
//$project_dir = "/home/osm/export-cadastre/";
//$data_path = "$temporary_dir/data/";
//$bin_path = "$project_dir/bin/";
//$logs_path = "$temporary_dir/logs/";
//$locks_path = "$temporary_dir/locks";
//
$config_handle=  fopen("../config", "r");
if ($config_handle) {
    while (($line = fgets($config_handle)) !== false) {
        $args = explode('=', $line, 2);
        $var_name = trim($args[0]);
        $$var_name = trim($args[1]);
    }
    fclose($config_handle);
} else {
    print("config file not found");
    exit(0);
}
umask(002);

// Set it to true when you have a doubt about Qadastre output
$do_we_log=false;

$dep_array=array(
	array("id" => "970", "name" => "970 Saint-Barth&eacute;l&eacute;my"),
	array("id" => "971", "name" => "971 Guadeloupe"),
	array("id" => "972", "name" => "972 Martinique"),
	array("id" => "973", "name" => "973 Guyane"),
	array("id" => "974", "name" => "974 R&eacute;union"),
	array("id" => "975", "name" => "975 Saint-Pierre-et-Miquelon"),
	array("id" => "976", "name" => "976 Mayotte"),
	array("id" => "001", "name" => "001 Ain"),
	array("id" => "002", "name" => "002 Aisne"),
	array("id" => "003", "name" => "003 Allier"),
	array("id" => "004", "name" => "004 Alpes-de-Haute-Provence"),
	array("id" => "005", "name" => "005 Hautes-Alpes"),
	array("id" => "006", "name" => "006 Alpes-maritimes"),
	array("id" => "007", "name" => "007 Ard&egrave;che"),
	array("id" => "008", "name" => "008 Ardennes"),
	array("id" => "009", "name" => "009 Ari&egrave;ge"),
	array("id" => "010", "name" => "010 Aube"),
	array("id" => "011", "name" => "011 Aude"),
	array("id" => "012", "name" => "012 Aveyron"),
	array("id" => "013", "name" => "013 Bouches-du-Rh&ocirc;ne"),
	array("id" => "014", "name" => "014 Calvados"),
	array("id" => "015", "name" => "015 Cantal"),
	array("id" => "016", "name" => "016 Charente"),
	array("id" => "017", "name" => "017 Charente-Maritime"),
	array("id" => "018", "name" => "018 Cher"),
	array("id" => "019", "name" => "019 Corr&egrave;ze"),
	array("id" => "02A", "name" => "02A Corse-du-Sud"),
	array("id" => "02B", "name" => "02B Haute-Corse"),
	array("id" => "021", "name" => "021 C&ocirc;te-d'Or"),
	array("id" => "022", "name" => "022 C&ocirc;tes-d'Armor"),
	array("id" => "023", "name" => "023 Creuse"),
	array("id" => "024", "name" => "024 Dordogne"),
	array("id" => "025", "name" => "025 Doubs"),
	array("id" => "026", "name" => "026 Dr&ocirc;me"),
	array("id" => "027", "name" => "027 Eure"),
	array("id" => "028", "name" => "028 Eure-et-Loir"),
	array("id" => "029", "name" => "029 Finist&egrave;re"),
	array("id" => "030", "name" => "030 Gard"),
	array("id" => "031", "name" => "031 Haute Garonne"),
	array("id" => "032", "name" => "032 Gers"),
	array("id" => "033", "name" => "033 Gironde"),
	array("id" => "034", "name" => "034 H&eacute;rault"),
	array("id" => "035", "name" => "035 Ille-et-Vilaine"),
	array("id" => "036", "name" => "036 Indre"),
	array("id" => "037", "name" => "037 Indre-et-Loire"),
	array("id" => "038", "name" => "038 Is&egrave;re"),
	array("id" => "039", "name" => "039 Jura"),
	array("id" => "040", "name" => "040 Landes"),
	array("id" => "041", "name" => "041 Loir-et-Cher"),
	array("id" => "042", "name" => "042 Loire"),
	array("id" => "043", "name" => "043 Haute-Loire"),
	array("id" => "044", "name" => "044 Loire Atlantique"),
	array("id" => "045", "name" => "045 Loiret"),
	array("id" => "046", "name" => "046 Lot"),
	array("id" => "047", "name" => "047 Lot et Garonne"),
	array("id" => "048", "name" => "048 Loz&egrave;re"),
	array("id" => "049", "name" => "049 Maine-et-Loire"),
	array("id" => "050", "name" => "050 Manche"),
	array("id" => "051", "name" => "051 Marne"),
	array("id" => "052", "name" => "052 Haute-Marne"),
	array("id" => "053", "name" => "053 Mayenne"),
	array("id" => "054", "name" => "054 Meurthe-et-Moselle"),
	array("id" => "055", "name" => "055 Meuse"),
	array("id" => "056", "name" => "056 Morbihan"),
	array("id" => "057", "name" => "057 Moselle"),
	array("id" => "058", "name" => "058 Ni&egrave;vre"),
	array("id" => "059", "name" => "059 Nord"),
	array("id" => "060", "name" => "060 Oise"),
	array("id" => "061", "name" => "061 Orne"),
	array("id" => "062", "name" => "062 Pas de Calais"),
	array("id" => "063", "name" => "063 Puy-de-D&ocirc;me"),
	array("id" => "064", "name" => "064 Pyr&eacute;n&eacute;es-Atlantiques"),
	array("id" => "065", "name" => "065 Haute-Pyr&eacute;n&eacute;es"),
	array("id" => "066", "name" => "066 Pyr&eacute;n&eacute;es-Orientales"),
	array("id" => "067", "name" => "067 Bas-Rhin"),
	array("id" => "068", "name" => "068 Haut-Rhin"),
	array("id" => "069", "name" => "069 Rh&ocirc;ne"),
	array("id" => "070", "name" => "070 Haute-Sa&ocirc;ne"),
	array("id" => "071", "name" => "071 Sa&ocirc;ne-et-Loire"),
	array("id" => "072", "name" => "072 Sarthe"),
	array("id" => "073", "name" => "073 Savoie"),
	array("id" => "074", "name" => "074 Haute-Savoie"),
	array("id" => "075", "name" => "075 Paris"),
	array("id" => "076", "name" => "076 Seine-Maritime"),
	array("id" => "077", "name" => "077 Seine-et-Marne"),
	array("id" => "078", "name" => "078 Yvelines"),
	array("id" => "079", "name" => "079 Deux-S&egrave;vres"),
	array("id" => "080", "name" => "080 Somme"),
	array("id" => "081", "name" => "081 Tarn"),
	array("id" => "082", "name" => "082 Tarn et Garonne"),
	array("id" => "083", "name" => "083 Var"),
	array("id" => "084", "name" => "084 Vaucluse"),
	array("id" => "085", "name" => "085 Vend&eacute;e"),
	array("id" => "086", "name" => "086 Vienne"),
	array("id" => "087", "name" => "087 Haute-Vienne"),
	array("id" => "088", "name" => "088 Vosges"),
	array("id" => "089", "name" => "089 Yonne"),
	array("id" => "090", "name" => "090 Territoire de Belfort"),
	array("id" => "091", "name" => "091 Essonne"),
	array("id" => "092", "name" => "092 Hauts-de-Seine"),
	array("id" => "093", "name" => "093 Seine-Saint-Denis"),
	array("id" => "094", "name" => "094 Val-de-Marne"),
	array("id" => "095", "name" => "095 Val-d'Oise")
);
