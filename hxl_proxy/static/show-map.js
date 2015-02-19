var map = L.map('map-div');

var osmUrl='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
var osmAttrib='Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
var osm = new L.TileLayer(osmUrl, {attribution: osmAttrib});
map.addLayer(osm);

$.get(csv_url, function(csvString) {
    var arrayData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
    var hxl = new HXLDataset(arrayData);

    var markers = new L.MarkerClusterGroup();
    var iterator = hxl.iterator();
    var seen_latlon = false;
    while (row = iterator.next()) {
        var lat = row.get('#lat_deg');
        var lon = row.get('#lon_deg');
        if (!isNaN(lat) && !isNaN(lon)) {
            seen_latlon = true;
            var marker = L.marker([lat, lon]);
            console.log(marker);
            marker.bindPopup('Location info');
            markers.addLayer(marker);
        }
    }
    if (seen_latlon) {
        map.addLayer(markers);
        map.fitBounds(markers.getBounds());
    } else {
        alert("No #lat_deg and #lon_deg values to map.");
    }
});
