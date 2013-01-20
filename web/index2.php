<?php 
include("includes/header.php");
include("includes/config.php");

if(isset($_POST["dep"])) $dep=$_POST["dep"];
if(isset($_POST["ville"])) $ville=$_POST["ville"];
?>

<div>
<p>
<?php
if(isset($dep) && isset($ville)) {
	if(!file_exists("locks/".$dep))
		mkdir("locks/".$dep);
	if(!file_exists("logs/".$dep))
		mkdir("logs/".$dep);
	if(file_exists("locks/".$dep."/".$dep."-".$ville.".lock")) {
		echo "Import en cours";
	}
	else {
		$log=fopen("logs/log.txt","a+");
		fwrite($log,date("d-m-Y H:i:s")." ".$_SERVER["REMOTE_ADDR"]." : ".$dep." ".$ville.";\n");
		fclose($log);
		$list=fopen("list.txt","a+");
		fwrite($list,$ville."\n");
		fclose($list);
		$list=fopen("list.txt","r");
		$nlist=substr_count(fread($list,filesize("list.txt")),"\n");
		fclose($list);
		echo "Import lanc&eacute;. Il y a ".$nlist." villes en attente";
	}
}
?>
</p>
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
		if(is_dir($data_path.$d["id"])) {
			if(!isset($d["name"]))
				$d["name"]=$d["id"];
			echo "\t\t\t<option value=\"".$d["id"]."\"";
			if(isset($dep) && $dep==$d["id"])
				echo " selected";
			echo ">".$d["name"]."</option>\n";
		}
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
	</fieldset>
	<div>
		<input type="submit" />
	</div>
</form>
<? include("includes/footer.php"); ?>
