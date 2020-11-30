<?php
require_once( 'includes/header.php' );
require_once( 'includes/config.php' );

function get_parameter($name, $format, $default_GET = "", $default_POST = null) {
	if ($default_POST === null) {
		$default_POST = $default_GET;
	}
        if (isset($_SERVER['REQUEST_METHOD']) &&
            ($_SERVER['REQUEST_METHOD'] == 'POST'))
        {
		if (isset($_POST[$name])) {
			$val = $_POST[$name];
		} else {
			$val = $default_POST;
		}
	} else {
		if (isset($_GET[$name])) {
			$val = $_GET[$name];
		} else {
			$val = $default_GET;
		}
	}
	if (($val != "") && (! preg_match($format, $val))) {
		echo "Erreur interne: ". $val . "<br/>\n";
		require_once( 'includes/footer.php' );
		exit(0);
	} else {
		return $val;
	}
}

$dep = get_parameter("dep", "/^([09][0-9][0-9AB])?$/");
$ville = get_parameter("ville", "/^[A-Z0-9][A-Z0-9][0-9][0-9][0-9][-a-zA-Z0-9_ '().]*$/");
$type = get_parameter("type", "/(^bati$)|(^adresses$)/", "bati");
$bis = get_parameter("bis","/(^true$)|(^false$)/", "true", "false");
$clean_osm_cache = get_parameter("clean_osm_cache","/(^true$)|(^false$)/", "false");
$bbox = get_parameter("bbox","/^[-0-9.,]*$/");
$force = get_parameter("force","/^(true)|(false)*$/","false");
$confirmAlreadyGenerated = false;
$command = "";

$num_dep = (substr($dep, 0, 1) == '0') ? substr($dep, 1) : $dep;
$insee = (substr($dep, 0, 1) == '0') ?
      (substr($dep, 1,2) . substr($ville, 2, 3))
    : (substr($dep, 0,2) . substr($ville, 2, 3));

function already_generated() {
  global $type;
  global $dep;
  global $ville;
  global $data_dir;
  $prefix = $data_dir . '/' . $dep . "/" . $ville;
  if ($type == "bati") {
	$fichiers = array(
		"-city-limit.osm",
		"-houses.osm");
  } else if ($type == "adresses") {
	$fichiers = array(
		"-adresses-addrstreet_mix_en_facade_ou_isole.zip",
		"-adresses-addrstreet_point_sur_batiment.zip",
		"-adresses-addrstreet_sans_batiment.zip",
		"-adresses-addrstreet_tag_sur_batiment.zip",
		"-adresses-associatedStreet_mix_en_facade_ou_isole.zip",
		"-adresses-associatedStreet_point_sur_batiment.zip",
		"-adresses-associatedStreet_sans_batiment.zip",
		"-adresses-associatedStreet_tag_sur_batiment.zip",
		"-adresses-lieux-dits.zip",
		"-mots.zip");
  } else {
    return false;
  }
  foreach($fichiers as $fichier) {
    //echo $prefix . $fichier . "<br/>";
    if ( ! file_exists($prefix . $fichier)) {
	  return false;
    }
  }
  return true;
}


function echo_data_file_row($name, $file_path) {
    global $data_dir;
    echo "<tr><td>$name: </td><td>";
    $link_path = $data_dir . '/' . $file_path;
    $link_url= "data" . '/' . $file_path;
    if (is_file($link_path)) {
        echo "<a href='data/$file_path'>" . basename($file_path) . "</a>";
    } else {
        echo '<font color="red" size="+1">&#x274C;</font> erreur';
    }
    echo "</td></tr>\n";
}

?>
<fieldset id="conditions-utilisation">
<legend>Note</legend>
<font size="-1">
Ce service et les données du cadastre disponibles ici sont exclusivement réservés à l'usage des contributeurs OpenStreetMap. <a href="https://wiki.openstreetmap.org/wiki/Cadastre_Fran%C3%A7ais/Conditions_d%27utilisation">En savoir plus.</a>
<br/>
<img src='images/info.png' alt='!' style='vertical-align:sub;' />
JOSM permet de télécharger directement les données du cadastre grâce au plug-in <a href="https://wiki.openstreetmap.org/wiki/FR:JOSM/Greffons/Cadastre-fr">Cadastre-fr <img src="https://wiki.openstreetmap.org/w/images/b/b8/Plugin_Cadastre_pour_JOSM.PNG" width="55" height="46" style="vertical-align:middle;"/></a>.
<br/>
<img src='images/info.png' alt='!' style='vertical-align:sub;' />
<a class="fantoir_ville_link" href="https://bano.openstreetmap.fr/fantoir/#insee=<?= $insee ?>">L'interface fatoir de BANO
<img src="images/bano_fantoir_adresses.png" style="vertical-align:middle;" width="66" height=25" border="1"/></a>
premet d'ajouter directement les adresses manquantes dans JOSM.
</font>
</fieldset>
<div id='information'>
<?php
if( $dep && $ville && $type )
{
	if( !file_exists( $lock_dir ) )
        {
		mkdir( $lock_dir );
        }
	if( !file_exists( $lock_dir . '/' . $dep ) )
	{
                #echo($lock_dir . '/' . $dep );
		mkdir( $lock_dir . '/' . $dep);
	}
	if( !file_exists( $log_dir ) )
        {
		mkdir( $log_dir );
        }
	if( !file_exists( $log_dir . '/' . $dep ) and $do_we_log )
	{
		mkdir( $log_dir . '/' . $dep);
	}
	$log_file = $log_dir . '/' . $dep . '/' . $dep . '-' . $ville . '-' . $type . '.log';
	$lock_file = $lock_dir . '/' . $dep . '/' . $dep . '-' . $ville . '-' . $type . '.lock';
	if( file_exists( $lock_file ) && ((time() - filemtime ( $lock_file )) < 2*60*60)) {
		echo 'Import en cours';
	}
	else if (($force != "true") && $bbox=="" && already_generated())
	{
	    $confirmAlreadyGenerated = true;
	}
	else
	{
		register_shutdown_function ( function($filepath) {@unlink($filepath);}, $lock_file );
		if( touch( $lock_file ) )
		{
			chmod( $lock_file, 0664);
			if ($do_we_log)
			{
				$log = fopen( $log_dir . '/log.txt', 'a+' );
				fwrite( $log, date( 'd-m-Y H:i:s' ) . ' ' . $_SERVER['REMOTE_ADDR'] . ' : ' . $dep . ' ' . $ville . "" . $type . ";\n" );
				fclose( $log );
				if ($type == "adresses") {
					$log_cmd="2>&1 |tee \"$log_file\"";
				} else {
					$log_cmd="> \"$log_file\" 2>&1";
				}
			}
			else
			{
				//if ($type == "adresses") {
					$log_cmd="2>&1";
				//} else {
				//	$log_cmd="> /dev/null 2>&1";
				//}
			}
			$v = explode( '-', $ville, 2 );
			if ($type == "adresses") {
				$command = sprintf( "cd %s && ./import-adresses.sh %s %s \"%s\" $bis $clean_osm_cache $log_cmd", $bin_dir, $dep, $v[0], trim( $v[1] ));
			} else {
				$command = sprintf( "cd %s && ./import-ville2.sh %s %s \"%s\" $bbox $log_cmd", $bin_dir, $dep, $v[0], trim( $v[1] ));
				//exec( $command );
				//echo 'Import ok. Acc&egrave;s <a href="data/' . $dep . '">aux fichiers</a> - <a href="data/' . $dep . '/' . $v[0] . '-' . trim( $v[1] ) . '.tar.bz2">&agrave; l\'archive</a>';
				//$command = '';
			}
		}
		else
			echo 'Something went wrong';
	}
}
?>
</div>

<!-- bbox selection -->
<div id="bbox_overlay"></div>
<div id="bbox_frame">
	<div id="bbox_title"><div>Sélectionnez la zone à exporter</div></div>
	<div id="bbox_map"></div>
	<div id="bbox_buttons">
		<span class="bbox_button" onclick="bbox_confirm();">OK</span>
		&nbsp;&nbsp;&nbsp;&nbsp;
		<span class="bbox_button" onclick="bbox_cancel();">Annuler</span>
	</div>
</div>


<form id='main_form' name='form-dep' action='' method='post'>
	<fieldset id='fdep'>
		<legend>Choix du d&eacute;partement</legend>
		<label>D&eacute;partement&nbsp;:</label>
		<select name='dep' id='dep' onchange='javascript:onDepartementChange();'>
			<option></option>
<?php
if( $handle = opendir( $data_dir ) )
{
	foreach( $dep_array as $d )
	{
		if( !isset( $d['name'] ) )
			$d['name'] = $d['id'];
		echo "\t\t\t" . '<option value="' . $d['id'] . '"';
		if( $dep == $d['id'] )
			echo ' selected="selected"';
		echo '>' . $d['name'] . "</option>\n";
	}
	closedir( $handle );
}
else
	echo 'No data';
?>
		</select>
		<input value="Recherche" type="text" id="recherche_dep" name="recherche_dep" maxlength="40" size="20" onfocus="javascript:if(this.value == 'Recherche') this.value='';" onchange="javascript:filter_dep();" onkeyup="javascript:filter_dep();" onpaste="javascript:filter_dep();" onmouseup="javascript:filter_dep();"/>
		<span class="stats_fantoir">
                  <a id="fantoir_dep_link" href="https://bano.openstreetmap.fr/fantoir/stats_dept.html#dept=<?= $num_dep ?>">Stats FANTOIR</a>
		  <br/>
                  <a id="fantoir_dep_recent_street_link" href="https://bano.openstreetmap.fr/fantoir/voies_recentes_manquantes.html#dept=<?= $num_dep ?>">Voies récentes manquantes</a>
		</span>
	</fieldset>
	<fieldset id='fville'>
		<legend>Choix de la commune</legend>
		<img src='images/throbber_16.gif' style='display:none;' alt='pending' id='throbber_ville' />
		<span id='ville_container'>
<?php
  include("getDepartement.php");
?>
		</span>
		<input value="Recherche" type="text" id="recherche_ville" name="recherche_ville" maxlength="60" size="20" onfocus="javascript:if(this.value == 'Recherche') this.value='';" onchange="javascript:filter_ville();" onkeyup="javascript:filter_ville();" onpaste="javascript:filter_ville();" onmouseup="javascript:filter_ville();"/>
		<span class="stats_fantoir">
                <a class="fantoir_ville_link" href="https://bano.openstreetmap.fr/fantoir/#insee=<?= $insee ?>">Stats FANTOIR BANO</a>
		</span>

		<br />
		<p style='font-size:small;'><img src='images/info.png' alt='!' style='vertical-align:sub;' />&nbsp;Le code indiqué à coté du nom de la commune est son <a href='https://fr.wikipedia.org/wiki/Code_Insee#Identification_des_collectivit.C3.A9s_locales_.28et_autres_donn.C3.A9es_g.C3.A9ographiques.29'>code INSEE</a>, pas son code postal</p>
		<p style='font-size:small;'>Seules les communes existant au format vecteur au cadastre sont listées</p>
	</fieldset>
	<fieldset id='ftype'>
		<legend>Choix du type de données</legend>
<?php
$bati_checked = ($type=="bati") ? 'checked="checked"' : '';
$adresses_checked = ($type=="adresses") ? 'checked="checked"' : '';
$bis_checked = ($bis=="true") ? 'checked="checked"' : "";
$clean_osm_cache_checked = ($clean_osm_cache=="true") ? 'checked="checked"' : "";
$bbox_checked = ($bbox!="") ? 'checked="checked"' : "";
?>
		<table border="0" cellspacing="0">
			<tr>
				<td>
					<input type="radio" name="type" value="adresses" <?php echo $adresses_checked;?>></input>Adresses
				</td><td>
					<small>(<input type="checkbox" name="bis" value="true" title="Transforme les lettres B,T,Q en bis, ter, quater" <?php echo $bis_checked;?>></input>B,T,Q&rarr; bis, ter, quater)</small>
					<small>(<input type="checkbox" name="clean_osm_cache" value="true" title="Effacer le cache de données OSM" <?php echo $clean_osm_cache_checked;?>></input>Effacer le cache de données OSM)</small>
				</td>
			</tr><tr>
				<td>
					<input type="radio" name="type" value="bati" <?php echo $bati_checked;?>></input>Bâti &amp; Limites
				</td><td>
					<small>(<input type="checkbox" id="bbox" name="bbox" value="<?php echo $bbox;?>" onchange="if (this.checked) bbox_display();" <?php echo $bbox_checked;?>></input>Sélectionner une zone à exporter)</small>
				</td>
			</tr>
		</table>
	</fieldset>
	<input id='force' type='hidden' name='force' value='false'/>
	<div id="generer">
		<input type='submit' value='Générer' onClick='return alert_if_not_city_selected();'/>&nbsp;&nbsp;
		<a href="#" id="info-button" onclick="toggle_info_popup();">?</a>
	</div>
</form>

<div id="info-popup" style="display:none">
    <button class="close-button" onclick="this.parentElement.style.display='none';">x</button>
    <fieldset id='mise_en_garde'>
	<legend>Mise en garde</legend>
	<ul>
	<li>L'intégration de données <i><u>bâtiments</u></i> en provenance du cadastre n'est pas triviale, si vous ne venez pas de <a href='https://wiki.openstreetmap.org/wiki/WikiProject_France/Cadastre/Import_semi-automatique_des_b%C3%A2timents' target="_blank">la page suivante</a>, il est vivement recommandé d'aller la lire !</li>
	<li>Pour les <i><u>limites</u></i> de communes, ce n'est pas trivial non plus et la <a href='https://wiki.openstreetmap.org/wiki/WikiProject_France/Limites_administratives/Tracer_les_limites_administratives' target="_blank">documentation est ici.</a></li>
	<li>Pour l'intégration des données <i><u>adresses</u></i>, <a href='https://wiki.openstreetmap.org/wiki/WikiProject_France/Cadastre/Import_semi-automatique_des_adresses' target="_blank">il faut lire cette page</a></li>
	</ul>
    </fieldset>
    <!--
    <fieldset id='temps'>
	<legend>Pour patienter pendant la génération</legend>
	<ul>
	<li>Vous pouvez aider à identifier des bâtiments OSM potentiellement fractionnés par le cadastre: <a href="segmented/" target="_blank">Bâtiments Fractionnés</a>
	</ul>
    </fieldset>
    -->
</div>
<script type='text/javascript'>
<?php
if ($ville) {
	echo "\tdocument.getElementById( 'ville' ).focus();\n";
} else {
	echo "\tdocument.getElementById( 'dep' ).focus();\n";
}
if ($command) {
	echo "\tdisplay_info_popup();\n";
}
?>
</script>
<?php
if ($command) {
    class ProcessLineReader {
      private $resource;
      private $pipes;
      function __construct($cmd) {
        $descriptorspec    = array(
          0 => array('pipe', 'r'),
          1 => array('pipe', 'w'),
          2 => array('pipe', 'w')
        );
        $this->resource = proc_open($cmd, $descriptorspec, $this->pipes);
        fclose($this->pipes[0]);
      }
      function readstd() {
        if ($this->resource !== FALSE) {
          return fgets($this->pipes[1]);
        } else {
          return FALSE;
        }
      }
      function readerror() {
        if ($this->resource !== FALSE) {
          return fgets($this->pipes[2]);
        } else {
          return FALSE;
        }
      }
      function close() {
              fclose($this->pipes[1]);
              fclose($this->pipes[2]);
              $status = proc_get_status($this->resource);
              proc_close($this->resource);
              $this->resource = FALSE;
              return $status['exitcode'];
      }
      function print_error_and_close() {
        while($line = $this->readerror()) {
          print "<pre>" . $line . "</pre>";
        }
        return $this->close();
      }
    }
    print "<pre>";
    $process = new ProcessLineReader("$command");
    ob_end_flush();
    flush();
    while($line = $process->readstd()) {
      print $line;
      flush();
    }
    $exitcode = $process->print_error_and_close();

    if ($type == "adresses") {
      $associatedStreet_files = array (
          "Mix en façade proche ou point isolé" => "$dep/$ville-adresses-associatedStreet_mix_en_facade_ou_isole.zip",
          //"Toujours en façade de bâtiment" => "$dep/$ville-adresses-associatedStreet_point_sur_batiment.zip",
          //"Toujours comme attribut de bâtiment" => "$dep/$ville-adresses-associatedStreet_tag_sur_batiment.zip",
          "Toujours comme point isolés" => "$dep/$ville-adresses-associatedStreet_sans_batiment.zip",
      );
      $addrstreet_files = array();
      foreach($associatedStreet_files as $key => $val) {
          $addrstreet_files[$key] = str_replace("associatedStreet","addrstreet",$associatedStreet_files[$key]);
      }
      print "</pre>\n";

      print "<fieldset>\n";
      echo "<legend>Résultat avec tag addr:street:</legend>\n";
      echo "<table class=\"result\">\n";
      foreach($addrstreet_files as $key => $val) {
        echo_data_file_row($key, $val);
      }
      echo "</table>\n";
      print "</fieldset>\n";
      print "<fieldset>\n";
      echo "<legend>Résultat avec relation associatedStreet:</legend>\n";
      echo "<table class=\"result\">\n";
      foreach($associatedStreet_files as $key => $val) {
        echo_data_file_row($key, $val);
      }
      echo "</table>\n";
      print "</fieldset>\n";

      print "<fieldset>\n";
      echo "<legend>Résultat de Lieux-Dits, tag place=...</legend>\n";
      echo "<table class=\"result\">\n";
      echo_data_file_row("Lieux-Dits","$dep/$ville-adresses-lieux-dits.zip");
      echo "</table>\n";
      print "</fieldset>\n";

      print "<fieldset>\n";
      echo "<legend>Liste de mots dessinés sur le cadastre (noms de rues, de lieux-dits ou autre)</legend>\n";
      echo "<table class=\"result\">\n";
      echo_data_file_row("Mots","$dep/$ville-mots.zip");
      echo "</table>\n";
      print "</fieldset>\n";
    } else {
      if ($exitcode == 0) {
        echo "Terminé.<br />";
      } else {
        echo "Erreur.<br />";
      }
    }
    ?>
    <script type='text/javascript'>
	document.getElementById('information').innerHTML = 'Import ok. Acc&egrave;s <a href="data/<?php echo $dep;?>">aux fichiers</a>';
        hide_info_popup();
        <?php if (($type == "adresses") || ($exitcode != 0)) { ?>
        window.scrollTo(0, document.body.scrollHeight);
        <?php } else { ?>
	document.location = "data/<?php echo $dep;?>";
	<?php } ?>
    </script>
    <?php
} else if ($confirmAlreadyGenerated) {
    ?>
    <script type='text/javascript'>
    	confirmAlreadyGenerated();
    </script>
    <?php
}
    ?>
<p>&nbsp;</p>
<?php
require_once( 'includes/footer.php' );
?>
