var map = L.map('map-div');
var map_markers = new L.MarkerClusterGroup();

var osmUrl='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
var osmAttrib='Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
var osm = new L.TileLayer(osmUrl, {attribution: osmAttrib});
map.addLayer(osm);

var map_layers = {};

function get_map_layer(name) {
    if (!map_layers[name]) {
        map_layers[name] = new L.layerGroup();
    }
    return map_layers[name];
}

$.get(csv_url, function(csvString) {
    var arrayData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
    var hxl = new HXLDataset(arrayData);

    var iterator = hxl.iterator();
    var seen_latlon = false;

    while (row = iterator.next()) {
        var layer = get_map_layer(row.get(map_layer_tag));
        var label = map_label_tags.map(function(tag) { return row.get(tag); }).join(', ');
        var lat = row.get('#lat_deg');
        var lon = row.get('#lon_deg');
        if (lat != null && !isNaN(lat) && lon != null && !isNaN(lon)) {
            var marker = L.marker([lat, lon]);
            marker.bindPopup(label);
            layer.addLayer(marker);
            seen_latlon = true;
        }
    }
    if (seen_latlon) {
        var overlays = {}
        for (name in map_layers) {
            map_markers.addLayer(map_layers[name]);
            overlays[name] = new L.layerGroup();
            map.addLayer(overlays[name]);
        }
        L.control.layers(null, overlays).addTo(map);

        map.on('overlayadd', function (event) {
            map_markers.addLayer(map_layers[event.name]);
        });

        map.on('overlayremove', function (event) {
            map_markers.removeLayer(map_layers[event.name]);
        });

        map.addLayer(map_markers);
        map.fitBounds(map_markers.getBounds());
    } else {
        alert("No #lat_deg and #lon_deg values to map.");
    }
});
