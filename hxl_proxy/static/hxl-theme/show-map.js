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

function make_hex(n) {
    var s = n.toString(16);
    if (s.length < 2) {
        s = '0' + s;
    }
    return s;
}

var map_type = 'choropleth';
var map_count_tag = '#x_count_num';

function make_color(value, min, max) {
    var range = max - min;
    var magnitude = value - min;
    var percentage = magnitude / range;
    var red = Math.floor(255 * percentage);
    var green = Math.floor(255 * (1 - percentage));
    return '#' + make_hex(red) + make_hex(green) + '00';
}

function make_popup(row) {
    var label = "<table class='map-popup'>\n";
    for (i in row.values) {
        column = row.columns[i];
        value = row.values[i];
        if (column.tag != '#lat_deg' && column.tag != '#lon_deg' && column.tag != '#x_bounds_js') {
            label += "  <tr>\n";
            if (column.header) {
                label += "    <th>" + column.header + "</th>\n";
            } else {
                label += "    <th>" + column.tag + "</th>\n";
            }
            label += "    <td>" + value + "</td>\n";
            label += "  </tr>\n";
        }
    }
    label += "</table>";
    return label;
}

if (map_type == 'choropleth') {
    $.get(csv_url, function(csvString) {
        var arrayData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
        var hxl = new HXLDataset(arrayData);
        var features = L.featureGroup([]);

        var min_value = hxl.getMin('#x_count_num');
        var max_value = hxl.getMax('#x_count_num');

        var iterator = hxl.iterator();
        while (row = iterator.next()) {
            bounds_str = row.get('#x_bounds_js');
            if (bounds_str) {
                var geometry = jQuery.parseJSON(bounds_str);
                var layer = L.geoJson(geometry, {
                    style: {
                        color: make_color(row.get('#x_count_num'), min_value, max_value),
                        opacity: 0.5,
                        weight: 2
                    }
                });
                layer.bindPopup(make_popup(row));
                features.addLayer(layer);
            }
            map.addLayer(features);
            map.fitBounds(features.getBounds());
        }
    });
} else {
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
}
