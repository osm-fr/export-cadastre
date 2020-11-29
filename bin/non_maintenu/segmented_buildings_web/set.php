<?php

/**
 * Record a contribution for the validation of segmented building cases.
 * 
 * Possible choices are 'join' 'keep' 'unknown'. 
 * The special choice  'back' allow to delete a previous contribution.  
 *
 * @param id the id of the segmentation cases.
 * @param choice 'join' 'keep' 'unknown' back'.
 * @param session a random 32 bit integer that need to match for 'back' choice.
 * 
 */

function fatal($message) { trigger_error($message, E_USER_ERROR); }

if ( ! (isset($_GET['choice']) && isset($_GET['id']) && isset($_GET['session']))) {
    fatal("wrong arguments");
}

$ip = $_SERVER['REMOTE_ADDR'];
$id = intval($_GET['id']);
$choice = $_GET['choice'];
$session = intval($_GET['session']);

if (in_array($choice, array('join', 'keep', 'unknown', 'back'))) {
    passthru(dirname(__FILE__) ."/../../bin/segmented_buildings/set.py --ip $ip --id $id --choice $choice --session $session", $retval);
    if ($retval != 0) {
        fatal("");
    }
/*
$dbstring=file_get_contents(dirname(__FILE__) .'/../../bin/segmented/.database-connection-string');
$db = pg_connect($dbstring);
if (!$db) fatal("DB connection problem");

if (in_array($choice, array('join', 'keep', 'unknown'))) {
    $query = <<<EOT
        INSERT INTO segmented_contributions 
        (case_id, ip, "time", choice, session)
        VALUES ($id, '$ip', now(), '$choice', $session);
EOT;
    $result = pg_query($db, $query);
    if (!$result) fatal('SQL query pb');

} else if ($choice == 'back') {

    $query = <<<EOT
        DELETE FROM segmented_contributions 
        WHERE case_id=$id AND ip='$ip' AND session=$session
        AND (now() - "time") < (interval '10 minute')
        AND "time"=(
                SELECT MAX("time") FROM segmented_contributions 
                WHERE case_id=$id AND ip='$ip' AND session=$session);
EOT;
    $result = pg_query($db, $query);
    if (!$result) fatal('SQL query pb');

*/
} else {
    fatal('wrong arguments');
}

?>
