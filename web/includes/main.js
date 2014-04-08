
var ville_filter;
var dep_filter;

var getDepartement_previous_depCode = '';
function getDepartement( ville )
{
        var depIndex = document.getElementById( "dep" ).selectedIndex;
        var depCode = document.getElementById( "dep" ).options[depIndex].value;
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
        //      document.getElementById("throbber_ville").style.display = "none";
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
