<?php 
include("includes/header.php");
include("includes/config.php");

if(isset($_POST["dep"])) $dep=$_POST["dep"];
if(isset($_POST["ville"])) $ville=$_POST["ville"];
?>

<div id="information">
<?php
if(isset($dep) && isset($ville)) {
	if(!file_exists("$locks_path/".$dep))
		mkdir("$locks_path/".$dep);
	if(!file_exists("$logs_path/".$dep))
		mkdir("$logs_path/".$dep);
	if(file_exists("$locks_path/".$dep."/".$dep."-".$ville.".lock")) {
		echo "Import en cours";
	}
	else {
		if(touch("$locks_path/".$dep."/".$dep."-".$ville.".lock")) {
			$log=fopen("$logs_path/log.txt","a+");
			fwrite($log,date("d-m-Y H:i:s")." ".$_SERVER["REMOTE_ADDR"]." : ".$dep." ".$ville.";\n");
			fclose($log);
			$v=explode('-',$ville,2);
			$command=sprintf("cd %s && ./import-ville.sh %s %s \"%s\" > \"$logs_path/%s/%s-%s.log\" 2>&1",$bin_path,$dep,$v[0],trim($v[1]),$dep,$dep,$ville);
			exec($command);
			echo "Import ok. Acc&egrave;s <a href=\"data/".$dep."\">aux fichiers</a> - <a href=\"data/".$dep."/".$v[0]."-".trim($v[1]).".tar.bz2\">&agrave; l'archive</a>";
			unlink("$locks_path/".$dep."/".$dep."-".$ville.".lock");
		}
		else {
			echo "Something went wrong";
		}
	}
}
?>
</div>

<form name="form-dep" action="" method="POST">
	<fieldset id="fdep">
		<legend>Choix du d&eacute;partement</legend>
		<label>D&eacute;partement&nbsp;:</label>
		<select name="dep" id="dep" onChange="javascript:getDepartement();">
			<option></option>
<?php
if($handle=opendir($data_path)) {
	foreach($dep_array as $d) {
		if(!isset($d["name"]))
			$d["name"]=$d["id"];
		echo "\t\t\t<option value=\"".$d["id"]."\"";
		if(isset($dep) && $dep==$d["id"])
			echo " selected";
		echo ">".$d["name"]."</option>\n";
	}
	closedir($handle);
}
else {
	echo "No data";
}
?>
		</select>
	</fieldset>
	<fieldset id="fville">
		<legend>Choix de la ville</legend>
		<select id="ville" name="ville">
		<img src="images/throbber_16.gif" style="display:none;" alt="pending" id="throbber_ville" />
	</select>
	<br /><p style="font-size:small;"><img src="images/info.png" alt="!" style="vertical-align:sub;" />&nbsp;Le code de la ville est son <a href="http://fr.wikipedia.org/wiki/Code_Insee#Identification_des_collectivit.C3.A9s_locales_.28et_autres_donn.C3.A9es_g.C3.A9ographiques.29">code INSEE</a>, pas son code postal</p>
	</fieldset>
	<fieldset id="mise_en_garde">
		<legend>Mise en garde</legend>
	<br /><p>
		L'intégration de données "batiments" en provenance du cadastre n'est pas triviale, si vous ne venez pas de <a href="http://wiki.openstreetmap.org/wiki/WikiProject_France/Cadastre/Import_semi-automatique_des_b%C3%A2timents">la page page suivante</a>, il est vivement recommandé d'aller la lire !
		</p
		<p>
		Pour les limites de communes, c'est pas trivial non plus et la <a href="http://wiki.openstreetmap.org/wiki/WikiProject_France/Limites_administratives/Tracer_les_limites_administratives">documentation est ici.</a>
	</p>
	</fieldset>
	<div>
		<input type="submit" />
	</div>
</form>
<p>
Note: Vous pensez avoir trouvé un bug ? <a href="http://trac.openstreetmap.fr/newticket">Vous pouvez le signaler ici (composant export cadastre)</a>
</p>
<? include("includes/footer.php"); ?>
