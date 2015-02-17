var map = L.map('map-div');

var osmUrl='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
var osmAttrib='Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
var osm = new L.TileLayer(osmUrl, {attribution: osmAttrib});
map.addLayer(osm);

$.get(csv_url, function(csvString) {
    alert("Got CSV");
    var arrayData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
    
    // loop
    var markers = new L.MarkerClusterGroup();
    var point = [51.5, -0.09];
    var marker = L.marker(point);
    marker.bindPopup('Location info');
    markers.addLayer(marker);
    // end loop
    
    map.addLayer(markers);
    map.fitBounds(markers.getBounds());
});
