<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
		<meta http-equiv="Content-Script-Type" content="text/javascript" />
		<meta http-equiv="Content-Style-Type" content="text/css" />
		<title>Interface de g&eacute;n&eacute;ration des fichiers d'import du cadastre</title>
		<link rel="stylesheet" type="text/css" media="screen" href="includes/style.css" />
		<script type="text/javascript" src="includes/main.js"></script>
		<link rel="stylesheet" href="http://cdn.leafletjs.com/leaflet-0.7.2/leaflet.css" />
		<script type="text/javascript" src="http://cdn.leafletjs.com/leaflet-0.7.2/leaflet.js"></script>
		<link rel="stylesheet" href="http://rawgit.com/tyndare/leaflet-areaselect/master/src/leaflet-areaselect.css"></link>
		<script type="text/javascript" src="http://rawgit.com/tyndare/leaflet-areaselect/master/src/leaflet-areaselect.js"></script>
	</head>
<body>
<div id="head">
	<h1>Interface de g&eacute;n&eacute;ration de fichiers .osm &agrave; partir du cadastre</h1>
	<ul>
		<li><a id="data_link" href="data">Acc&egrave;s aux donn&eacute;es</a></li>
	</ul>
</div>
<div id="main">
