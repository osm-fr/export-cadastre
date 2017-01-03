<?php

/**
 * Return stats on contributors.
 *
 * This file is largely derived from OpenSolarMap backend code: 
 * https://github.com/opensolarmap/solback/blob/master/solback.py 
 */

function fatal($message) { trigger_error($message, E_USER_ERROR); }

header('Content-Type: application/json');

$ip = $_SERVER['REMOTE_ADDR'];

passthru(dirname(__FILE__) ."/../../bin/segmented_buildings/stats.py --ip $ip", $retval);
if ($retval != 0) {
    fatal("");
}

?>
