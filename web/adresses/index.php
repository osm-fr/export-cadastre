<?php 
require_once( 'includes/header.php' );
require_once( 'includes/config.php' );

if( isset( $_POST['dep'] ) )
	$dep = $_POST['dep'];
if( isset( $_POST['ville'] ) )
	$ville = $_POST['ville'];
$command = "";
?>
<div id="conditions-utilisation">
<p>
Ce service et les données du cadastre disponibles ici sont exclusivement réservés à l'usage des contributeurs OpenStreetMap. <a href="http://wiki.openstreetmap.org/wiki/Cadastre_Fran%C3%A7ais/Conditions_d%27utilisation">En savoir plus</a>
</p>
</div>
<div id='information'> 
<?php
if( isset( $dep ) && isset( $ville ) )
{
	if( !file_exists( $locks_path . '/' . $dep ) )
	{
		@mkdir( $locks_path );
		mkdir( $locks_path . '/' . $dep );
	}
	if( !file_exists( $logs_path . '/' . $dep ) and $do_we_log )
	{
		@mkdir( $logs_path );
		mkdir( $logs_path . '/' . $dep );
        }
	$lock_file = $locks_path . '/' . $dep . '/' . $dep . '-' . $ville . '-adresses.lock';
	if( file_exists( $lock_file ) && ((time() - filemtime ( $lock_file )) < 60*60)) {
		echo 'Import en cours';
        }
	else
	{
		if( touch( $lock_file ) )
		{
		        chmod( $lock_file, 0664);
			if ($do_we_log)
			{
				$log = fopen( $logs_path . '/log-adresses.txt', 'a+' );
				fwrite( $log, date( 'd-m-Y H:i:s' ) . ' ' . $_SERVER['REMOTE_ADDR'] . ' : ' . $dep . ' ' . $ville . ";\n" );
				fclose( $log );
				$import_adresse_logs="2>&1 |tee \"$logs_path/%s/%s-%s-adresses.log\" 2>&1";
			}
			else
				$import_adresses_logs="";
			$v = explode( '-', $ville, 2 );
			$command = sprintf( "cd %s && ./import-adresses.sh %s %s \"%s\" $import_adresses_logs", $bin_path, $dep, $v[0], trim( $v[1] ), $dep, $dep, $ville );
			//exec( $command );
			//echo 'Import ok. Acc&egrave;s <a href="data/' . $dep . '">aux fichiers</a> - <a href="data/' . $dep . '/' . $v[0] . '-' . trim( $v[1] ) . '.tar.bz2">&agrave; l\'archive</a>';
			//unlink( $lock_file );
		}
		else
			echo 'Something went wrong';
	}
}
?>
</div>

<form name='form-dep' action='' method='POST'>
	<fieldset id='fdep'>
		<legend>Choix du d&eacute;partement</legend>
		<label>D&eacute;partement&nbsp;:</label>
		<select name='dep' id='dep' onChange='javascript:getDepartement();'>
			<option></option>
<?php
if( $handle = opendir( $data_path ) )
{
	foreach( $dep_array as $d )
	{
		if( !isset( $d['name'] ) )
			$d['name'] = $d['id'];
		echo "\t\t\t" . '<option value="' . $d['id'] . '"';
		if( isset( $dep ) && $dep == $d['id'] )
			echo ' selected="selected"';
		echo '>' . $d['name'] . "</option>\n";
	}
	closedir( $handle );
}
else
	echo 'No data';
?>
		</select>
	</fieldset>
	<fieldset id='fville'>
		<legend>Choix de la commune</legend>
		<img src='images/throbber_16.gif' style='display:none;' alt='pending' id='throbber_ville' />
		<select id='ville' name='ville'>
		</select>
		<br />
		<p style='font-size:small;'><img src='images/info.png' alt='!' style='vertical-align:sub;' />&nbsp;Le code indiqué à coté du nom de la commune est son <a href='http://fr.wikipedia.org/wiki/Code_Insee#Identification_des_collectivit.C3.A9s_locales_.28et_autres_donn.C3.A9es_g.C3.A9ographiques.29'>code INSEE</a>, pas son code postal</p>
		<p style='font-size:small;'>Seules les communes existant au format vecteur au cadastre sont listées</p>
	</fieldset>
	<fieldset id='mise_en_garde'>
		<legend>Mise en garde</legend>
		<br />
		<p>
		L'intégration de données 'adresses' en provenance du cadastre n'est pas triviale, si vous ne venez pas de <a href='http://wiki.openstreetmap.org/wiki/WikiProject_France/Cadastre/Import_semi-automatique_des_adresses'>la page suivante</a>, il est vivement recommandé d'aller la lire !
		</p>
	</fieldset>
	<div>
		<input type='submit' value='Générer' />
	</div>
</form>
<p>
Note: Vous pensez avoir trouvé un bug ? <a href='http://trac.openstreetmap.fr/newticket?component=export%20cadastre&owner=vdct'>Vous pouvez le signaler ici (composant export cadastre)</a>
</p>
<?php
if( $_POST['ville'] )
{
?>
<script type='text/javascript'>
	getDepartement( '<?php echo $ville; ?>' ); 
</script>
<?php
}
if ($command) {
    class ProcessLineReader {
      private $resource;
      private $pipes;
      private $state;
      function __construct($cmd) {
        $descriptorspec    = array(
          0 => array('pipe', 'r'),
          1 => array('pipe', 'w'),
          2 => array('pipe', 'w')
        );
        $this->resource = proc_open($cmd, $descriptorspec, $this->pipes);
        $state = 1;
        fclose($this->pipes[0]);
      }
      function readstd() {
        if ($this->resource !== FALSE) {
          return fgets($this->pipes[1]);
        } else {
          return $FALSE;
        }
      }
      function readerror() {
        if ($this->resource !== FALSE) {
          return fgets($this->pipes[2]);
        } else {
          return $FALSE;
        }
      }
      function close() {
              fclose($this->pipes[1]);
              fclose($this->pipes[2]);
              proc_close($this->resource);
              $this->resource = FALSE;
      }
      function print_error_and_close() {
        while($line = $this->readerror()) {
          print "<pre>" . $line . "</pre>";
        }
        $this->close();
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
    $process->print_error_and_close();
    unlink( $lock_file );

    $associatedStreet_files = array (
        "Sans bâtiment" => "/data/$dep/$ville-adresses-associatedStreet_sans_batiment.zip",
        "Point sur bâtiment" => "/data/$dep/$ville-adresses-associatedStreet_point_sur_batiment.zip",
        "Tag sur bâtiment" => "/data/$dep/$ville-adresses-associatedStreet_tag_sur_batiment.zip"
    );
    $addrstreet_files = array();
    foreach($associatedStreet_files as $key => $val) {
        $addrstreet_files[$key] = str_replace("associatedStreet","addrstreet",$associatedStreet_files[$key]);
    }
    print "</pre>\n";
    print "<fieldset>\n";
    echo "<legend>Résultat avec tag addr:street:</legend>\n";
    echo "<ul>\n";
    foreach($addrstreet_files as $key => $val) {
        echo "<li>$key: <a href='$val'>" . basename($val) . "</a></li>\n";
    }
    echo "</ul>\n";
    print "</fieldset>\n";
    print "<fieldset>\n";
    echo "<legend>Résultat avec relation associatedStreet:</legend>\n";
    echo "<ul>\n";
    foreach($associatedStreet_files as $key => $val) {
        echo "<li>$key: <a href='$val'>" . basename($val) . "</a></li>\n";
    }
    echo "</ul>\n";
    print "</fieldset>\n";
    ?>
    <script type='text/javascript'>
    	document.getElementById('information').innerHTML = 'Import ok. Acc&egrave;s <a href="/data/<?php echo $dep;?>">aux fichiers</a>';
    </script>
    <?php
}
require_once( 'includes/footer.php' );
