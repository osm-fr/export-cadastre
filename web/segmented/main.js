const map1 = L.map('map1');
const map2 = L.map('map2', { zoomControl: false });
map1.attributionControl.setPrefix("")
map2.attributionControl.setPrefix("")
map1.setView([18.227, -61.645], 13);
map2.setView([18.227, -61.645], 13);
map1.sync(map2);
map2.sync(map1);


let photo_layer, photo_attrib;
if (window.location.hostname == 'cadastre.openstreetmap.fr') {
    photo_layer = 'http://proxy-ign.openstreetmap.fr/bdortho/{z}/{x}/{y}.jpg';
    photo_attrib = '&copy; <a href="http://openstreetmap.fr/bdortho">BDOrtho IGN</a>';
} else {
    photo_layer = 'http://{s}.tiles.mapbox.com/v4/openstreetmap.map-inh7ifmo/{z}/{x}/{y}.png?access_token=pk.eyJ1Ijoib3BlbnN0cmVldG1hcCIsImEiOiJncjlmd0t3In0.DmZsIeOW-3x-C5eX-wAqTw';
    photo_attrib = '&copy; <a href="https://www.mapbox.com/satellite/">Mapbox/DigitalGlobe</a>';
}
L.tileLayer(photo_layer, {
    attribution: photo_attrib,
    maxNativeZoom: 19,
    maxZoom: 24,
    minZoom: 3
}).addTo(map1);
L.tileLayer('http://tms.cadastre.openstreetmap.fr/*/tout/{z}/{x}/{y}.png', {
    attribution: '&copy <a href="http://wiki.openstreetmap.org/wiki/Cadastre_Fran%C3%A7ais/Conditions_d%27utilisation">Direction Générale des Finances Publiques - Cadastre</a>',
    maxNativeZoom: 21,
    maxZoom: 24,
    minZoom: 3
}).addTo(map2);


class GeometryError extends Error {
    constructor(message) {
        super(message);
        this.name = 'GeometryError';
    }
}

class ConnectionError extends Error {
    constructor(message) {
        super(message);
        this.name = 'ConnectionError';
    }
}

const style_big = { color: 'blue', stroke: true, fill: false, weight:4 };
const style_small = { color: 'lightgreen', stroke: true, fill: false , weight:4};
const style_keep = { color: 'lightgreen', stroke: true, fill: false , weight:7};
const style_join = { color: 'red', stroke: true, fill: false, weight:6};
const style_none = { stroke: false };
const style_unknown = { color: 'yellow', stroke: true, fill: false, weight:3};

/**
 * Leaflet Polylines for 2 polygons to be joined.
 */
class JoinPolygons {
    constructor(latLngs1, latLngs2) {
        [this.outer1_latLngs, this.outer2_latLngs, this.intersect_latLngs] = JoinPolygons.get_outers_and_intersect_latLngs(latLngs1, latLngs2);
        this.outer1_polylines = []
        this.outer2_polylines = []
        this.intersect_polylines = []
        this.blinkOn = false;
        this.blinkInterval = null;
        let outer1_size = JoinPolygons.length(this.outer1_latLngs);
        let outer2_size = JoinPolygons.length(this.outer2_latLngs);
        if (outer1_size > outer2_size) {
            this.style_outer1 = style_big;
            this.style_outer2 = style_small
        } else {
            this.style_outer1 = style_small;
            this.style_outer2 = style_big;
        }
    }

    addTo(map) {
        this.outer1_polylines.push(L.polyline(this.outer1_latLngs, this.style_outer1).addTo(map));
        this.outer2_polylines.push(L.polyline(this.outer2_latLngs, this.style_outer2).addTo(map));
        this.intersect_polylines.push(L.polyline(this.intersect_latLngs, style_join).addTo(map));
        return this;
    }

    on(type, func, context) {
        this.outer1_polylines.forEach(p => p.on(type, func, context));
        this.outer2_polylines.forEach(p => p.on(type, func, context));
        this.intersect_polylines.forEach(p => p.on(type, func, context));
        return this;
    }

    remove() {
        this.outer1_polylines.forEach(p => p.remove());
        this.outer2_polylines.forEach(p => p.remove());
        this.intersect_polylines.forEach(p => p.remove());
        clearInterval(this.blinkInterval);
    }

    blink() {
        this.blinkOn = !this.blinkOn;
        this.outer1_polylines.forEach(p => p.setStyle(this.blinkOn ? this.style_outer1 : style_unknown));
        this.outer2_polylines.forEach(p => p.setStyle(this.blinkOn ? this.style_outer2 : style_unknown));
        this.intersect_polylines.forEach(p => p.setStyle(this.blinkOn ? style_small : style_none));
    }

    showBlinking() {
        clearInterval(this.blinkInterval);
        this.blinkOn = false;
        this.blink();
        this.blinkInterval = setInterval(() => this.blink(), 500);
    }

    showJoined() {
        clearInterval(this.blinkInterval);
        this.outer1_polylines.forEach(p => p.setStyle(style_join));
        this.outer2_polylines.forEach(p => p.setStyle(style_join));
        this.intersect_polylines.forEach(p => p.setStyle(style_none));
    }

    showKept() {
        clearInterval(this.blinkInterval);
        this.outer1_polylines.forEach(p => p.setStyle(this.style_outer1));
        this.outer2_polylines.forEach(p => p.setStyle(this.style_outer2));
        this.intersect_polylines.forEach(p => p.setStyle(style_keep));
    }

    getBounds() {
        return this.outer1_polylines[0].getBounds().pad(0).extend(this.outer2_polylines[0].getBounds());
    }

    getCenter() {
        return this.intersect_polylines[0].getCenter();
    }

    static length(latLngs) {
        latLngs = latLngs.map(c => L.latLng(c));
        let result = 0;
        for(let i=1;i<latLngs.length;i++) {
            result = result + latLngs[i].distanceTo(latLngs[i-1]);
        }
        return result;
    }

    /**
     * Takes 2 touching polygons as input, and returns the
     * joined version, and the intesrsect section.
     */
    static get_outers_and_intersect_latLngs(way1, way2) {
        function latLng_eq(p1, p2) {
            return (p1[0] == p2[0]) && (p1[1] == p2[1])
        }

        function is_closed(way) {
            return latLng_eq(way[0], way[way.length - 1]);
        }

        if (!(is_closed(way1) && is_closed(way2))) {
            throw new GeometryError("not closed polygons");
        }
        way1 = way1.slice(1);
        way2 = way2.slice(1);
        if (way1.length < way2.length) {
            let w = way1;
            way1 = way2;
            way2 = w;
        }
        const length1 = way1.length;
        const length2 = way2.length

        // rotate way1 so that it starts with a point not common with way2:
        let i1 = way1.findIndex(p1 => way2.findIndex(p2 => latLng_eq(p1, p2)) < 0);
        if (i1 == -1) {
            throw new GeometryError("no distincts points");
        }
        way1 = way1.slice(i1, length1).concat(way1.slice(0, i1));

        // get the intersection points (the points common to the two ways)
        const intersect = way1.filter(p1 => way2.findIndex(p2 => latLng_eq(p1, p2)) >= 0);

        // rotate way1 so that it starts with the first intersecting point:
        i1 = way1.findIndex(p1 => latLng_eq(p1, intersect[0]));
        if (i1 == -1) {
            throw new GeometryError("no common points");
        }
        way1 = way1.slice(i1, length1).concat(way1.slice(0, i1));

        // get the outer part of way1
        const outer1 = way1.filter(p1 => intersect.findIndex(p2 => latLng_eq(p1, p2)) < 0);


        // rotate and reverse way2 so that it starts with the first intersecting point:
        let i2 = way2.findIndex(p2 => latLng_eq(intersect[0], p2));
        if (latLng_eq(way2[(i2 + 1) % length2], intersect[1])) {
            way2.reverse();
            i2 = length2 - 1 - i2;
        }
        way2 = way2.slice(i2, length2).concat(way2.slice(0, i2));

        // get the outer part of way2
        const outer2 = way2.filter(p2 => intersect.findIndex(p1 => latLng_eq(p1, p2)) < 0)

        // join outer1 and outer2 
        //const joined = [intersect[intersect.length-1]].concat(outer1).concat([intersect[0]]).concat(outer2).concat([intersect[intersect.length-1]]);

        const full_outer1 = intersect.slice(-1).concat(outer1).concat(intersect.slice(0, 1));
        const full_outer2 = intersect.slice(0, 1).concat(outer2).concat(intersect.slice(-1));

        return [full_outer1, full_outer2, intersect];
    }
}


/**
 * Increase a LatLngBounds size by the given meters, and then the given factor,
 * and make it square.
 * It is intended to be an improovement for our use of the original 
 * LatLngBounds.pad() method.
 */
function betterPad(latLngBounds, meters, factor) {
    cur_width_meters = latLngBounds.getSouthWest().distanceTo(latLngBounds.getSouthEast());
    cur_height_meters = latLngBounds.getSouthWest().distanceTo(latLngBounds.getNorthWest());
    let cur_size_meters = latLngBounds.getSouthWest().distanceTo(latLngBounds.getNorthEast());
    let new_size_meters = (cur_size_meters + meters) * (1 + factor);
    let center = latLngBounds.getCenter();
    new_width_deg = (latLngBounds.getEast()-center.lng) * new_size_meters / cur_width_meters;
    new_height_deg = (latLngBounds.getNorth()-center.lat) * new_size_meters / cur_height_meters;
    return L.latLngBounds(
        L.latLng(center.lat - new_height_deg, center.lng - new_width_deg),
        L.latLng(center.lat + new_height_deg, center.lng + new_width_deg));
};
 


let joinPolygons = null;
document.getElementById('button-join').addEventListener("mouseenter", function() {
    if (joinPolygons != null) joinPolygons.showJoined();
});
document.getElementById('button-keep').addEventListener("mouseenter", function() {
    if (joinPolygons != null) joinPolygons.showKept();
});
document.getElementById('button-join').addEventListener("mouseleave", function() {
    if (joinPolygons != null) joinPolygons.showBlinking();
});
document.getElementById('button-keep').addEventListener("mouseleave", function() {
    if (joinPolygons != null) joinPolygons.showBlinking();
});
document.getElementById('button-join').addEventListener("click", () => choose("join", false));
document.getElementById('button-keep').addEventListener("click", () => choose("keep", false));
document.getElementById('button-unknown').addEventListener("click", () => choose("unknown", false));
document.getElementById('button-back').addEventListener("click", () => go_back(false));
document.body.addEventListener("keydown", function(e) {
    switch (e.keyCode) {
        case 48:
        case 96:
            choose("unknown", true);
            break;
        case 49:
        case 97:
            choose("join", true);
            break;
        case 50:
        case 98:
            choose("keep", true);
            break;
        case 8:
            go_back(true);
    }
});

function display_case(item) {
    if (joinPolygons != null) joinPolygons.remove();
    location.hash = item.id;
    joinPolygons = new JoinPolygons(item.coords1, item.coords2).addTo(map1).addTo(map2);
    joinPolygons.on("click", function() {
        window.open("https://www.openstreetmap.org/way/" + item.id1, "_blank");
        window.open("https://www.openstreetmap.org/way/" + item.id2, "_blank");});
    map1.fitBounds(betterPad(joinPolygons.getBounds(), 5, 0.2));
    document.getElementById('josm-link').href = josm_url(betterPad(joinPolygons.getBounds(), 30, 0.5), [item.id1, item.id2]);
    document.getElementById('osm-edit-link').href = osm_url(joinPolygons.getCenter(), map1.getZoom());
    joinPolygons.showBlinking();
}

function osm_url(latLng, zoom) {
    return "https://www.openstreetmap.org/edit?" +
        "lat=" + latLng.lat +
        "&lon=" + latLng.lng +
        "&zoom=" + zoom;
}

function josm_url(bounds, ways_id) {
    return "http://localhost:8111/load_and_zoom?" +
        "left=" + bounds.getWest() +
        "&bottom=" + bounds.getSouth() +
        "&right=" + bounds.getEast() +
        "&top=" + bounds.getNorth() +
        "&select=" + ways_id.map(id => "way" + id).join(",");
}

let cases = [];
let cases_ids = new Set();
let cur_index = -1;
let request_send = false;
let need_display = false;
let got_connection_error = false;

function set_next_case_the_nearest() {
    const center = map1.getCenter();
    const distances = cases.slice(cur_index).map(c => c.latLng.distanceTo(center));
    const nearest = distances.indexOf(Math.min(...distances));
    if (nearest > 0) {
        let next_case = cases[cur_index + nearest];
        cases[cur_index + nearest] = cases[cur_index];
        cases[cur_index] = next_case;
    }
}

function try_display_next(findNearest) {
    try {
        if (findNearest) set_next_case_the_nearest();
        display_case(cases[cur_index]);
    } catch (err) {
        //console.log(err.name);
        if (err.name == 'GeometryError') {
            console.log("Invalid geometry: ", cases[cur_index].id);
            // Invalid item
            cases.splice(cur_index, 1);
            cur_index = cur_index - 1;
            next(findNearest, null);
        } else {
            throw err;
        }
    }
}

function check_ok(fetch_response) {
    if (!fetch_response.ok) {
        throw new ConnectionError(fetch_response.statusText);
    }
    return fetch_response;
}

function connection_problem(err) {
    if ((err.name == 'ConnectionError') || (err.name == "TypeError")) {
        got_connection_error = true;
        alert("Problème de connection au serveur: " + err);
    } else {
        throw err;
    }
}

function next(findNearest, id) {
    //console.log("next " + findNearest + ", " + id);
    cur_index = cur_index + 1;
    if (id !== null) {
        // Remove all the following items
        cases.splice(cur_index).forEach(c => cases_ids.delete(c.id));
    }
    if (cur_index < cases.length) {
        try_display_next(findNearest);
    } else {
        need_display = true;
    }
    if ((!request_send && ((cur_index + 5) >= cases.length)) || (id != null))  {
        let url;
        if (id  == null) {
            const center = map1.getCenter();
            url = "get.php?limit=20&lat=" + center.lat + "&lon=" + center.lng;
        } else {
            url = "get.php?id=" + id + "&limit=1";
        }
        console.log(url);
        request_send = true;
        fetch(url).then((response => check_ok(response).json())).then(function(json) {
            //console.log("got " + json.features.length + " results");
            const new_cases = json.features
                .filter(feature => (feature.id == id) || (!cases_ids.has(feature.id)))
                .map(feature => {
                    return {
                        id: feature.id,
                        latLng: L.latLng(feature.properties.lat, feature.properties.lon),
                        id1: feature.properties.way1,
                        id2: feature.properties.way2,
                        coords1: feature.geometry.geometries[0].coordinates[0],
                        coords2: feature.geometry.geometries[1].coordinates[0],
                    };
                });
            console.log("new_cases " +  new_cases.length);
            cases = cases.concat(new_cases);
            new_cases.forEach(c => cases_ids.add(c.id));
            request_send = false;
            if (need_display) {
                need_display = false;
                if (cur_index < cases.length) {
                    try_display_next(findNearest);
                } else {
                    if (id == null) {
                        alert("Il ne reste pour le moment plus aucun cas à traiter. Bravo à tous !");
                    } else {
                        alert("Cas inconnu");
                        next(findNearest, null);
                    }
                }
            }
        }).catch(connection_problem);
        fetch_stats();
    }
}

function press(button) {
    button.classList.add("choice-button-active");
    setTimeout(() => button.classList.remove("choice-button-active"), 300);
}

const session = Math.round(Math.random() * 2147483647);

function show_reward(rewardid) {
    const elem = document.getElementById(rewardid);
    elem.style.display = "block";
    setTimeout(function() {
        elem.classList.add("reward-zoom");
        setTimeout(function() {
            elem.classList.remove("reward-zoom");
            elem.style.display = "none";
        }, 1000);
    }, 50);
}

function choose(choice, animate) {
    //console.log(choice);
    if ((cur_index >= 0) && (cur_index < cases.length)) {
        if (animate) press(document.getElementById("button-" + choice));
        url = "set.php?id=" + cases[cur_index].id + "&choice=" + choice + "&session=" + session;
        //console.log(url);
        fetch(url, { method: 'POST' }).then(r => check_ok(r)).catch(connection_problem);
        increment_stats(+1);
        show_reward((choice == "join") ? "plusone" : "plusok");
        next(true, null);
    }
}

function go_back(animate) {
    //console.log("back");
    if (cur_index >= 1) {
        if (animate) press(document.getElementById("button-back"));
        url = "set.php?id=" + cases[cur_index - 1].id + "&choice=back" + "&session=" + session;
        //console.log(url);
        fetch(url, { method: 'POST' }).then(r => check_ok(r)).catch(connection_problem);
        cur_index = cur_index - 2;
        increment_stats(-1);
        next(false, null);
    }
}

let stats = {
    contributions_distinct_ips: null,
    cases: null,
    contributions: null,
    contributions_distinct_cases: null,
    contributions_from_ip: 0,
}

function fetch_stats() {
    fetch("stats.php").then((response => check_ok(response).json())).then(function(json) {
        Object.keys(json).forEach(function (key) { stats[key] = json[key]; });
        show_stats();
    });
}

function increment_stats(value) {
    stats.contributions_from_ip += value;
    stats.contributions_distinct_cases += value;
    show_stats();
}

function show_stats() {
    document.getElementById("count_users").innerHTML = stats.contributions_distinct_ips;
    document.getElementById("count_cases").innerHTML = 
        stats.contributions_distinct_cases + " / " + stats.cases;
    document.getElementById("count_ip").innerHTML = stats.contributions_from_ip;
}


window.addEventListener("hashchange", function() { 
    id = parseInt(location.hash.substring(1));
    if ((id != parseInt("")) && (cur_index < cases.length) && (id != cases[cur_index].id)) {
        next(false, id);
    }
});

next(false, (location.hash.length > 0) ? parseInt(location.hash.substring(1)) :null);
