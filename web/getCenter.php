<?php
include( 'includes/config.php' );

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
$ville = get_parameter('ville', '/^[A-Z0-9][A-Z0-9][0-9][0-9][0-9][-a-zA-Z0-9_ \'()]*$/');
$ville = substr($ville,0, 5);

if ($ville && $dep) {
	$command = sprintf('%s/cadastre-housenumber/bin/cadastre_center.py "%s" "%s"', $bin_path, $dep, $ville);
	passthru($command);
}

?>
