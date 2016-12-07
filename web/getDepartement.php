<?php
include( 'includes/config.php' );

if (!isset($dep)) {
  function get_parameter($name, $format, $default = "") {
	  if (isset($_GET[$name])) {
		  $val = $_GET[$name];
	  } else {
		  $val = $default;
	  }
	  if (($val != "") && (! preg_match($format, $val))) {
		  echo 'Erreur interne: '. $val . '<br/>';
		  exit(0);
	  } else {
		  return $val;
	  }
  }

  $dep = get_parameter('dep', '/^([09][0-9][0-9AB])?$/');
  $ville = get_parameter('ville', '/^[A-Z0-9][A-Z0-9][0-9][0-9][0-9][-a-zA-Z0-9_ \'().]*$/');
}

// A cause de ce bug sur Internet Explorer
// (http://support.microsoft.com/kb/276228/fr)
// nous retournons l'élément <select> entier:
?>
		<select id='ville' name='ville' onchange="javascript:onVilleChange();">
<?php

if( $villes_file = fopen( $data_path . $dep . '/' . $dep . '-liste.txt','r' ) )
{

	while( $v = fgets( $villes_file ) )
	{
		$data = explode( ' ', $v, 3 );
		$villes_array[] = array( 'id' => $data[1], 'name' => trim( str_replace( '"', '', $data[2] ) ) );
	}
	fclose( $villes_file );
	foreach( $villes_array as $key => $v )
	{
		$id[$key]  = $v['id'];
		$name[$key] = trim( str_replace( '"','',$v['name'] ) );
	}

	array_multisort( $name, SORT_ASC, $id, SORT_ASC, $villes_array );
	foreach( $villes_array as $v )
	{
		echo "\t\t\t" . '<option value="' . $v['id'] . '-' . $v['name'] . '"';
		if( isset( $ville ) && $ville == $v['id'] . '-' . $v['name'] )
			echo ' selected="selected"';
		if( substr( $dep, 0, 1 ) == '0' )
			$insee_dep = substr( $dep, 1, 2 );
		else
			$insee_dep = substr( $dep, 0, 2 );
		$v['INSEEcode'] = $insee_dep . substr( $v['id'], 2, 3 );
		echo '>' . $v['name'] . '-' . $v['INSEEcode'] . "</option>\n";
	}

}

?>
		</select>

