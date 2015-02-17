var map = L.map('map-div');

var osmUrl='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
var osmAttrib='Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
var osm = new L.TileLayer(osmUrl, {attribution: osmAttrib});
map.addLayer(osm);

$.get(csv_url, function(csvString) {
    var arrayData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
    lat_index = hxl_get_tag_index(arrayData, '#lat_deg');
    lon_index = hxl_get_tag_index(arrayData, '#lon_deg');

    if (lat_index == null || lon_index == null) {
        alert("Dataset must have #lat_deg and #lon_deg tags for mapping.");
        return;
    }

    var markers = new L.MarkerClusterGroup();
    for (i = lat_index[0] + 1; i < arrayData.length; i++) {
        row = arrayData[i];
        lat = 0.0 + row[lat_index[1]];
        lon = 0.0 + row[lon_index[1]];
        var marker = L.marker([lat, lon]);
        marker.bindPopup('Location info');
        markers.addLayer(marker);
    }
    map.addLayer(markers);
    map.fitBounds(markers.getBounds());
});

function hxl_get_tag_index(data, tag) {
    for (i = 0; i < 2; i++) {
        for (j = 0; j < data[i].length; j++) {
            if (data[i][j] == tag) {
                return [i, j];
            }
        }
    }
    return null;
}
