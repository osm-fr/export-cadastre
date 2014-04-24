<?php
include( 'includes/config.php' );

if( isset( $_REQUEST['dep'] ) && ($_REQUEST['dep'] != ""))
	$dep = $_REQUEST['dep'];
else
{
	echo 'No dep';
	exit();
}

if( isset( $_REQUEST['ville'] ) )
	$ville = $_REQUEST['ville'];

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
			echo ' selected';
		if( substr( $dep, 0, 1 ) == '0' )
			$insee_dep = substr( $dep, 1, 2 );
		else
			$insee_dep = substr( $dep, 0, 2 );
		$v['INSEEcode'] = $insee_dep.substr( $v['id'], 2, 3 );
		echo '>' . $v['name'] . '-' . $v['INSEEcode'] . "</option>\n";
	}
}
else
	echo 'No data';
