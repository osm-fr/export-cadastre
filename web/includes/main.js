
var ville_filter;
var dep_filter;
var bbox_map = null;
var bbox_map_areaSelect = null;

function getSelectedDepCode() {
	var depIndex = document.getElementById( "dep" ).selectedIndex;
	return document.getElementById( "dep" ).options[depIndex].value;
}

function getSelectedVilleCode() {
	var villeIndex = document.getElementById( "ville" ).selectedIndex;
	if (villeIndex < 0) {
		return "";
	} else {
		return document.getElementById( "ville" ).options[villeIndex].value;
	}
}

function getSelectedInseeCode() {
	var dep = getSelectedDepCode();
	var ville = getSelectedVilleCode();
	if ((dep.length === 3) && (ville.length >= 5)) {
		if (dep.charAt(0) == '0') {
			return dep.substr(1,2) + ville.substr(2,3);
		} else {
			return dep.substr(0,2) + ville.substr(2,3);
		}
	} else {
		return "";
	}
}

function updateFantoirVilleLink() {
	var insee = getSelectedInseeCode();
	var fantoir_url = "https://bano.openstreetmap.fr/fantoir/#insee=" + insee;
	//document.getElementById("fantoir_ville_link").href = fantoir_url;
	var fantoir_ville_links = document.getElementsByClassName("fantoir_ville_link");
	for (var i=0; i<fantoir_ville_links.length; i++) {
		fantoir_ville_links[i].href = fantoir_url;
	}
}

var onDepartementChange_previous_depCode = '';
function onDepartementChange() {
	var depCode = getSelectedDepCode();
	if (depCode != onDepartementChange_previous_depCode) {
		onDepartementChange_previous_depCode = depCode;
		document.getElementById("data_link").href = "data/" + depCode + "/";
		document.getElementById("fantoir_dep_link").href = "https://bano.openstreetmap.fr/fantoir/stats_dept.html#dept=" + (depCode.startsWith("0") ? depCode.substr(1) : depCode);
		document.getElementById("fantoir_dep_recent_street_link").href = "https://bano.openstreetmap.fr/fantoir/voies_recentes_manquantes.html#dept=" + (depCode.startsWith("0") ? depCode.substr(1) : depCode);
		downloadVilleForDepartement(depCode);
	}
}

function downloadVilleForDepartement(depCode)
{
	//document.getElementById("throbber_ville").style.display = "inline";
	var xhr = new XMLHttpRequest();
	xhr.onreadystatechange = downloadVilleForDepartement_handler;
	xhr.open("GET", "getDepartement.php?dep=" + depCode);
	xhr.send();
}

function downloadVilleForDepartement_handler()
{
	if( this.readyState == 4 && this.status == 200 )
	{
		// A cause de ce bug sur Internet Explorer 8 et 9
		// (https://support.microsoft.com/kb/276228/fr)
		// on remplace le innerHTML du <span id="ville_container">
		// au lieu de remplacer celui du <select id="ville">:
		document.getElementById( "ville_container" ).innerHTML = this.responseText;
		ville_filter = new SelectBoxFilter(document.getElementById( "ville" ));
		document.getElementById( "recherche_ville" ).value = 'Recherche';
		updateFantoirVilleLink();
		//document.getElementById("throbber_ville").style.display = "none";
	}
}

function onVilleChange() {
	document.getElementById('bbox').checked=false;
	updateFantoirVilleLink();
}



function normalize(text) {
	text = text.toLowerCase();
	text = text.replace(/[-_']/g,' ');
	text = text.replace(/[aàÀ]/g,'a');
	text = text.replace(/[éèêëÉÈÊË]/g,'e');
	text = text.replace(/[ïîÏÎ]/g,'i');
	text = text.replace(/[ôÔ]/g,'o');
	text = text.replace(/[ùÙûÛ]/g,'u');
	text = text.replace(/\bsaint\b/g,'st');
	return text;
}

function SelectBoxFilter(selectbox) {
	this.selectbox = selectbox;
	this.optionscopy = new Array();
	for(var i=0; i<selectbox.options.length; i++) {
		var option = selectbox.options[i];
		this.optionscopy[i] = new Option(option.text, option.value);
	}
	this.previous_filter_reg_exp_source = '';
	this.filter = function(reg_exp) {
		if (reg_exp.source != this.previous_filter_reg_exp_source) {
			this.previous_filter_reg_exp_source = reg_exp.source;
			var selectedValue = this.selectbox.value;
			var selectedIndex = 0;
			this.selectbox.options.length = 0;
			var nb = 0;
			var nbvalue = 0;
			for(var i=0; i<this.optionscopy.length; i++) {
				option = this.optionscopy[i];
				if((option.value == "") || (normalize(option.text).search(reg_exp) != -1)) {
					if (option.value != "") nbvalue++;
					if (option.value == selectedValue) selectedIndex = nb;
					this.selectbox.options[nb++] = new Option(option.text, option.value, false);
				}
			}
			this.selectbox.selectedIndex = selectedIndex;
			if (nbvalue == 1) {
				this.selectbox.className = "selectboxfilter_found";
			} else if (nbvalue == 0) {
				this.selectbox.className = "selectboxfilter_notfound";
			} else {
				this.selectbox.className = "";
			}
			this.selectbox.onchange();
		}
	}
}

function filter_dep() {
	var text = document.getElementById("recherche_dep").value
	if (text != "Recherche") {
	var dep = document.getElementById("dep");
	if (typeof dep_filter == 'undefined') {
		dep_filter = new SelectBoxFilter(dep);
	}
	// recherche en début de mot (ou avec un 0 pour les code de département):
	dep_filter.filter(new RegExp("\\b0?" + normalize(text)));
	if (dep.options.length == 2) {
		dep.selectedIndex = 1;
		onDepartementChange();
	}
	}
}

function filter_ville() {
	var text = document.getElementById("recherche_ville").value
	if (text != "Recherche") {
		var ville = document.getElementById("ville");
		if (typeof ville_filter == 'undefined') {
			ville_filter = new SelectBoxFilter(ville);
		}
		// recherche en début de mot:
		ville_filter.filter(new RegExp("\\b" + normalize(text)));
	}
}

function alert_if_not_city_selected() {
	if ((getSelectedDepCode() == "") || (getSelectedVilleCode() == "")) {
	if (getSelectedDepCode() == "") {
		alert("Veuillez commencer par choisir le département et la commune");
	} else {
		alert("Veuillez d'abord choisir la commune");
	}
		return false;
	} else {
		return true;
	}
}

function bbox_display() {
	if ( ! alert_if_not_city_selected()) {
		return bbox_cancel();
	}
	insee = getSelectedInseeCode();
	document.getElementById("bbox_overlay").style.display = 'block';
	document.getElementById("bbox_frame").style.display = 'block';
	if (bbox_map == null) {
		var osmUrl='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
		var osmAttrib='Map data © <a href="https://openstreetmap.org">OpenStreetMap</a> contributors';
		var osm = new L.TileLayer(osmUrl, {minZoom: 2, maxZoom: 17, attribution: osmAttrib});
		bbox_map = L.map('bbox_map');
		bbox_map.addLayer(osm);
		bbox_map_areaSelect = L.areaSelect({width:300, height:200});
		bbox_map_areaSelect.addTo(bbox_map);
	}
	// récupère la position de la commune sélectionnée avec une requête overpass
	var xmlhttp=new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
		if (xmlhttp.readyState == 4) {
			bbox_map_setViewOnOverpassResult(xmlhttp.responseText);
		}
	};
	// Requête overpass pour chercher la relation avec "ref:INSEE"=insee
	xmlhttp.open("GET", "https://overpass-api.de/api/interpreter?data=[out:json];relation[boundary%3Dadministrative][%22ref%3AINSEE%22%3D%22" + insee + "%22]%3Bout center%3B");
	xmlhttp.send();
}

function bbox_confirm() {
	document.getElementById("bbox_frame").style.display = 'none';
	document.getElementById("bbox_overlay").style.display = 'none';
	try {
		bbox = bbox_map_areaSelect.getBounds().toBBoxString();
		if (bbox) {
			document.getElementById("bbox").value = bbox;
			document.getElementById("bbox").setAttribute("value",bbox);
			document.getElementById("bbox").setAttribute("checked","checked");
		} else {
			document.getElementById("bbox").checked = false;
		}
	} catch(err) {
		alert(err);
		document.getElementById("bbox").checked = false;
	}
}

function bbox_cancel() {
	document.getElementById("bbox_frame").style.display = 'none';
	document.getElementById("bbox_overlay").style.display = 'none';
	document.getElementById("bbox").checked = false;
}

function bbox_map_setViewOnOverpassResult(overpass_json_text) {
	result = JSON.parse(overpass_json_text);
	if (result.elements.length > 0) {
		var center = result.elements[0].center;
		bbox_map.setView([center.lat, center.lon], 15);
	} else {
		// call getCenter.php to get cadastre center
		var xmlhttp=new XMLHttpRequest();
		xmlhttp.onreadystatechange = function() {
			if (xmlhttp.readyState == 4) {
				bbox_map_setViewOnCenterResult(xmlhttp.responseText);
			}
		};
		var dep = getSelectedDepCode();
		var ville = getSelectedVilleCode();
		xmlhttp.open("GET", "getCenter.php?dep=" + dep + "&ville=" + ville);
		xmlhttp.send();
	}
}

function bbox_map_setViewOnCenterResult(response) {
	if (response.match(/[-0-9.,]*/)) {
		var values = response.split(",");
			bbox_map.setView([parseFloat(values[0]), parseFloat(values[1])], 14);
		} else {
			// centre sur la France:
			bbox_map.setView([46.0, 2], 6);
	}
}

function confirmAlreadyGenerated() {
	if (confirm("Les fichiers ont déjà été générés. Êtes-vous sûre de vouloir les générer de nouveau ?")) {
		document.getElementById("force").value = "true";
		document.forms["main_form"].submit();
	} else {
		window.location="data/" + getSelectedDepCode() + "/";
	}
}

function display_info_popup() {
	document.getElementById('info-popup').style.display="block";
}
function hide_info_popup() {
	document.getElementById('info-popup').style.display="none";
}
function toggle_info_popup() {
	var popup = document.getElementById('info-popup')
	if (popup.style.display == "none") {
		popup.style.display="block";
	} else {
		popup.style.display="none";
	}
}
