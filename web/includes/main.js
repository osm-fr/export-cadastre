
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
	var insee;
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

var getDepartement_previous_depCode = '';
function getDepartement( ville )
{
	var depCode = getSelectedDepCode();
	if (depCode != getDepartement_previous_depCode) {
		getDepartement_previous_depCode = depCode;
		var params = "dep=" + depCode;
		//document.getElementById("throbber_ville").style.display = "inline";
		var xhr = new XMLHttpRequest();
		xhr.onreadystatechange = handler;
		xhr.open("POST", "getDepartement.php?ville=" + ville, true );
		xhr.setRequestHeader( "Content-type", "application/x-www-form-urlencoded" );
		xhr.setRequestHeader( "Content-length", params.length );
		xhr.setRequestHeader( "Connection", "close" );
		xhr.send(params);
	}
}

function handler()
{
	if( this.readyState == 4 && this.status == 200 )
	{
		var ville = document.getElementById( "ville" );
		ville.innerHTML = this.responseText;
		ville_filter = new SelectBoxFilter(ville);
		document.getElementById( "recherche_ville" ).value = 'Recherche';
		filter_ville();
		//document.getElementById("throbber_ville").style.display = "none";
	}
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
      getDepartement();
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

function bbox_display() {
	insee = getSelectedInseeCode();
	if (insee == "") {
		return bbox_cancel();
	}
	document.getElementById("bbox_overlay").style.display = 'initial';
	document.getElementById("bbox_frame").style.display = 'initial';
	if (bbox_map == null) {
		var osmUrl='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
		var osmAttrib='Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
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
	// Requête overpass pour chercher un nœeud "place" avec "ref:INSEE"=insee
	xmlhttp.open("GET", "http://overpass-api.de/api/interpreter?data=[out:json];node[%22ref%3AINSEE%22%3D%22" + insee + "%22][%22place%22]%3Bout%3B");
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
      document.getElementById("bbox").setAttribute("checked","true");
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
		var center = result.elements[0];
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
