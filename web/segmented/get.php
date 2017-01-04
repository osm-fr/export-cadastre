<?php

/**
 * Return a geoJSON file representing the next 
 * segmented building cases to consider.
 *
 * @param limit max number of cases to return (integer).
 * @param lat latitude coordinates of the prefered location to look for new cases.
 * @param lon idem for longitude.
 * @param id of a particular case to get (optional param)
 *
 * This file is largely derived from OpenSolarMap backend code: 
 * https://github.com/opensolarmap/solback/blob/master/solback.py 
 */

function fatal($message) { trigger_error($message, E_USER_ERROR); }

header('Content-Type: application/vnd.geo+json');

$ip = $_SERVER['REMOTE_ADDR'];
$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 1;
if ($limit > 100) $limit = 100;
$default_lat = 48.3;
$default_long = -1.8;
$lat = isset($_GET['lat']) ? floatval($_GET['lat']) : $default_lat;
$lon = isset($_GET['lon']) ? floatval($_GET['lon']) : $default_long;
$id  = isset($_GET['id']) ? intval($_GET['id']) : -1;

passthru(dirname(__FILE__) ."/../../bin/segmented_buildings/get.py --ip $ip --limit $limit --lat $lat --lon $lon --id $id", $retval);
if ($retval != 0) {
    fatal("");
}

/*
$dbstring=file_get_contents(dirname(__FILE__) .'/../../bin/segmented/.database-connection-string');
$db = pg_connect($dbstring);
if (!$db) fatal("DB connection problem");
$items = array();

$output_format = <<<EOT
    '{"type":"Feature","id":'|| id::text
      ||',"properties":{'
      ||'"lat":'|| round(st_y(center)::numeric,7)::text
      ||',"lon":'|| round(st_x(center)::numeric,7)::text
      ||',"way1":'|| way1_osm_id::text 
      ||',"way2":'|| way2_osm_id::text 
      ||'},"geometry":{"type":"GeometryCollection","geometries":['
      ||st_asgeojson(way1_geom,7) || ','
      ||st_asgeojson(way2_geom,7) 
      ||']}}'
EOT;

# get a case from the allready partially crowdsourced ones
$query =  <<<EOT
    SELECT $output_format
    FROM segmented_contributions_next n
    LEFT JOIN segmented_contributions co ON (co.case_id=n.case_id and co.ip='$ip')
    JOIN segmented_cases ca ON (ca.id=n.case_id)
    WHERE n.total<10 AND co.ip is null
    GROUP BY ca.id, ca.way1_geom, ca.way2_geom, n.nb, n.last, ca.resolution
    HAVING resolution = 'none'
    ORDER BY n.nb desc, n.last limit $limit;
EOT;
$result = pg_query($db, $query);
#echo $query . "<br />\n";
#echo "nb result = " . pg_num_rows($result) . "<br />\n";
if (!$result) fatal("SQL query 1 pb");
$limit = $limit - pg_num_rows($result);
while ($row = pg_fetch_row($result)) array_push($items, json_decode($row[0]));

if ($limit > 0) {
    # get cases around our location
    $order = "ST_Distance(center,ST_SetSRID(ST_MakePoint($lon,$lat),4326))/(coalesce(n.nb,0)*10+1)";
    $query =  <<<EOT
        SELECT $output_format
        FROM segmented_cases ca
        LEFT JOIN segmented_contributions c1 ON (id=c1.case_id and c1.ip='$ip')
        LEFT JOIN segmented_contributions c2 ON (id=c2.case_id)
        LEFT JOIN segmented_contributions_next n ON (n.case_id=ca.id AND n.nb>=0)
        WHERE ca.resolution = 'none'
        AND coalesce(n.total,0)<10 AND c1.ip IS NULL
        GROUP by id, center, n.nb, n.last
        HAVING (count(c2.*)<10 or (count(distinct(c2.choice))=1 AND count(c2.*)<=3))
        ORDER BY $order LIMIT $limit;
EOT;
    #echo $query . "<br />\n";
    $result = pg_query($db, $query);
    if (!$result) fatal("SQL query 2 pb");
    $limit = $limit - pg_num_rows($result);
    #echo "nb result = " . pg_num_rows($result) . "<br />\n";
    #while ($row = pg_fetch_row($result)) add_item($row[0]);
    while ($row = pg_fetch_row($result)) array_push($items, json_decode($row[0]));
}

echo json_encode(array('type' => 'FeatureCollection', 'count' => count($items), 'features' => $items)); 
*/
?>
