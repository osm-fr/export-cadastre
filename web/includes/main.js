function getDepartement() {
	depIndex = document.getElementById("dep").selectedIndex;
	params = "dep=" + document.getElementById("dep").options[depIndex].value;
	//document.getElementById("throbber_ville").style.display = "inline";
	xhr = new XMLHttpRequest();
	xhr.onreadystatechange = handler;
	xhr.open("POST", "getDepartement.php",true);
	xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
	xhr.setRequestHeader("Content-length", params.length);
	xhr.setRequestHeader("Connection", "close");
	xhr.send(params);
}

function handler() {
	if(this.readyState == 4 && this.status == 200) {
		document.getElementById("ville").innerHTML = this.responseText;
	//	document.getElementById("throbber_ville").style.display = "none";
	}
}
