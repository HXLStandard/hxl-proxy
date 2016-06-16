////////////////////////////////////////////////////////////////////////
// JavaScript library for the HXL Proxy
//
// All functions and varibles appear as properties of the hxl_proxy
// object.
////////////////////////////////////////////////////////////////////////


/**
 * Root object for all HXL Proxy functions and variables.
 */
var hxl_proxy = {};


/**
 * General configuration parameters
 */
hxl_proxy.config = {
        gdriveDeveloperKey: 'UNSPECIFIED',
        gdriveClientId: 'UNSPECIFIED'
};


//
// Choosers
//

/**
 * Dataset-chooser functions
 */
hxl_proxy.choosers = {};


/**
 * Select a resource from the Humanitarian Data Exchange
 *
 * @param elementId the HTML id of the form input element where
 * the URL should appear.
 * @param submit if true, submit the form on success (default: false)
 * @returns always false.
 */
hxl_proxy.choosers.hdx = function(elementId, submit) {
    hdx.choose(function (resource) {
        var url = 'https://data.hdx.rwlabs.org/dataset/' + resource.package_id + '/resource/' + resource.id
        $(elementId).val(url);
        if (submit) {
            $(elementId).closest('form').submit();
        }
    });
    return false;
};


/**
 * Select a file from Dropbox.
 *
 * @param elementId the HTML id of the form input element where
 * the URL should appear.
 * @param submit if true, submit the form on success (default: false)
 * @returns always false.
 */
hxl_proxy.choosers.dropbox = function(elementId, submit) {
    Dropbox.choose({
        success: function(files) {
            $(elementId).val(files[0].link)
            if (submit) {
                $(elementId).closest('form').submit();
            }
        }
    });
    return false;
};


//
// UI
//

/**
 * User-interface functions.
 */
hxl_proxy.ui = {};


/**
 * Select a spreadsheet from Google Drive
 *
 * Relies on the hxl_proxy.config.gdriveDeveloperKey and the
 * hxl_proxy.config.gdriveClientId properties.
 *
 * Google makes this very difficult (compared to Dropbox).
 *
 * @param elementId the HTML id of the form input element where
 * the URL should appear.
 * @param submit if true, submit the form on success (default: false)
 * @returns always false.
 */
hxl_proxy.choosers.googleDrive = function(elementId, submit) {

    // We want to see only spreadsheets
    var scope = ['https://www.googleapis.com/auth/drive.readonly'];

    var pickerApiLoaded = false;
    var oauthToken = null;

    // Make a picker
    function createPicker() {
        if (pickerApiLoaded && oauthToken) {
            var view = new google.picker.DocsView(google.picker.ViewId.SPREADSHEETS);
            view.setMode(google.picker.DocsViewMode.LIST);
            var picker = new google.picker.PickerBuilder().
                addView(view).
                enableFeature(google.picker.Feature.NAV_HIDDEN).
                setOAuthToken(oauthToken).
                setDeveloperKey(hxl_proxy.config.gdriveDeveloperKey).
                setCallback(callback).
                build();
            picker.setVisible(true);
            // kludge to make sure it's in front of any modals
            $('.picker-dialog').css('z-index', '3000');
        }
    }

    // Handle the authorisation, if needed
    function onAuthApiLoad() {
        window.gapi.auth.authorize(
            {
                'client_id': hxl_proxy.config.gdriveClientId,
                'scope': scope,
                'immediate': false
            },
            function(authResult) {
                if (authResult && !authResult.error) {
                    oauthToken = authResult.access_token;
                    createPicker();
                }
            }
        );
    }

    // On success, create the picker.
    function onPickerApiLoad() {
        pickerApiLoaded = true;
        createPicker();
    }

    // Put the URL in the specified element
    function callback(data) {
        var url, doc;
        if (data[google.picker.Response.ACTION] == google.picker.Action.PICKED) {
            doc = data[google.picker.Response.DOCUMENTS][0];
            if (doc) {
                $(elementId).val(doc[google.picker.Document.URL]);
                if (submit) {
                    $(elementId).closest('form').submit();
                }
            }
        }
    }

    // Execute the commands.
    gapi.load('auth', {'callback': onAuthApiLoad});
    gapi.load('picker', {'callback': onPickerApiLoad});
    return false;
};


/**
 * Set up a page containing a form.
 * External dependencies: none
 */
hxl_proxy.ui.form = function() {

    function setup_fieldset(node, index) {
        filter_name = $(node).find(".field_filter select").val();
        filter_desc = $(node).find(".field_filter option:selected").text();
        filter_class = ".fields-" + filter_name;
        filter_title = (filter_desc ? filter_desc : '(not set)');
        if (filter_title == '(none)') {
            filter_title = "Add new filter";
        }
        $(node).find(".modal-title").text(filter_title);

        var filter_button = $(node).find(".filter-button");
        filter_button.text(filter_title);
        if (filter_name) {
            filter_button.removeClass("btn-default")
            filter_button.addClass("btn-primary")
        } else {
            filter_button.removeClass("btn-primary")
            filter_button.addClass("btn-default")
        }
        $(node).find(".hideable").hide();
        $(node).find(".hideable").find(hxl_proxy.field_types).prop("disabled", true);
        $(node).find(filter_class).show();
        $(node).find(filter_class).find(hxl_proxy.field_types).prop("disabled", false);
    };

    hxl_proxy.field_types = "input,select"
    $(".hideable").hide();
    $("#filter-form div.filter").each(function (index) {
        var filter_node = this;
        setup_fieldset(filter_node, index);
        $(filter_node).find(".field_filter select").on("change", function () {
            setup_fieldset(filter_node, index);
        })
    });
};


/**
 * Set up a page containing a chart.
 * External dependencies: Google Charts, JQuery, HXL
 * @param params.data_url URL to a CSV HXL dataset
 * @param params.type currently "pie", "bar", or "column" (defaults to "pie")
 * @param params.count_pattern HXL tag pattern to count.
 * @param params.filter_rule HXL rule for filtering.
 * @param params.label_pattern HXL tag pattern for the column containing labels (defaults to first column)
 * @param params.value_pattern HXL tag pattern for the column containing values (defaults to a numbery column, if present)
 */
hxl_proxy.ui.chart = function(params) {

    // Callback that creates and populates a data table,
    // instantiates the pie chart, passes in the data and
    // draws it.
    function drawChart() {

        function get_label_pattern(hxl) {
            if (params.label_pattern && hxl.hasColumn(params.label_pattern)) {
                return params.label_pattern;
            } else {
                // FIXME - just defaulting to first tag for now
                return hxl.columns[0].tag;
            }
        }

        function get_value_pattern(data) {
            if (params.value_pattern && data.hasColumn(params.value_pattern)) {
                return params.value_pattern;
            } else {
                var pattern = hxl.classes.Pattern.parse('#meta+count');
                for (i in data.columns) {
                    if (pattern.match(data.columns[i]) || data.isNumbery(data.columns[i].displayTag)) {
                        return data.columns[i].displayTag;
                    }
                }
            }
            alert("Can't guess numeric column for charting.");
            throw "Can't guess numeric column for charting.";
        }

        $.get(params.data_url, function(csvString) {
            var rawData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
            var hxlData = hxl.wrap(rawData);

            if (params.filter_pattern) {
                // If we have a filter pattern, apply it first
                if (params.filter_value) {
                    // If there's a value, use it to filter
                    hxlData = hxlData.withRows(params.filter_pattern + '=' + params.filter_value);
                } else if (!params.count_pattern && params.label_pattern) {
                    // If there's no value and we're not counting rows, sum up the results
                    hxlData = hxlData.count(params.label_pattern, get_value_pattern(hxlData));
                    for (var i in hxlData.columns) {
                        column = hxlData.columns[i]
                        if (column.attributes.indexOf('sum') != -1) {
                            params.value_pattern = column.displayTag;
                            break;
                        }
                    }
                }
            }
            if (params.count_pattern) {
                hxlData = hxlData.count(params.count_pattern);
            }
            var label_pattern = get_label_pattern(hxlData);
            var value_pattern = get_value_pattern(hxlData);
            var value_column = hxlData.getMatchingColumns(value_pattern)[0];
            var title = '';
            if (value_column.header) {
                title = value_column.header + ' (' + value_column.displayTag + ')';
            } else {
                title = value_column.displayTag;
            }

            var chartData = [[label_pattern, value_pattern]];
            var iterator = hxlData.iterator();
            while (row = iterator.next()) {
                var label = String(row.get(label_pattern));
                var value = row.get(value_pattern);
                if (!isNaN(value)) {
                    chartData.push([label, 0 + value]);
                }
            }

            var data = google.visualization.arrayToDataTable(chartData);

            if (params.type == 'bar') {
                options = {
                    title: title,
                    width: '100%',
                    height: hxlData.getRows().length * 40,
                    chartArea: {
                        top: 50
                    },
                    legend: {
                        position: 'none'
                    }
                }
                var chart = new google.visualization.BarChart(document.getElementById('chart_div'));
            } else if (params.type == 'column') {
                options = {
                    title: title,
                    width: hxlData.getRows().length * 60,
                    chartArea: {
                        top: 50,
                        left: 50
                    },
                    legend: {
                        position: 'none'
                    }
                }
                var chart = new google.visualization.ColumnChart(document.getElementById('chart_div'));
            } else {
                if (params.type && params.type != 'pie') {
                    alert("Unknown chart type: " + params.type + "\nPlease use 'bar', 'column', or 'pie'");
                }
                options = {
                    title: title,
                    width: '100%',
                    height: '100%',
                    chartArea: {
                        top: 50,
                        left: 50,
                    }
                }
                var chart = new google.visualization.PieChart(document.getElementById('chart_div'));
            }

            chart.draw(data, options);
        }).fail(function () {
            alert("Failed to load dataset " + params.data_url);
            throw "Failed to load dataset " + params.data_url;
        });
    }

    // Load the Visualization API and the piechart package.
    google.load('visualization', '1.0', {'packages':['corechart']});

    // Set a callback to run when the Google Visualization API is loaded.
    google.setOnLoadCallback(drawChart);

};


/**
 * Set up a page containing a map.
 * External dependencies: Leaflet, Leaflet marker cluster plugin, JQuery, HXL
 */
hxl_proxy.ui.map = function(params) {

    /**
     * Generate a heat-map colour.
     */
    function makeColor(value, min, max) {

        /**
         * Generate a colour from a gradiant using a colour map.
         * Adapted from http://stackoverflow.com/posts/7128796/revisions
         */
        function genColor(percentage, colorMap) {
            for (var i = 1; i < colorMap.length - 1; i++) {
                if (percentage < colorMap[i].percentage) {
                    break;
                }
            }
            var lower = colorMap[i - 1];
            var upper = colorMap[i];
            var range = upper.percentage - lower.percentage;
            var rangePercentage = (percentage - lower.percentage) / range;
            var percentageLower = 1 - rangePercentage;
            var percentageUpper = rangePercentage;
            var color = {
                r: Math.floor(lower.color.r * percentageLower + upper.color.r * percentageUpper),
                g: Math.floor(lower.color.g * percentageLower + upper.color.g * percentageUpper),
                b: Math.floor(lower.color.b * percentageLower + upper.color.b * percentageUpper)
            };
            return 'rgb(' + [color.r, color.g, color.b].join(',') + ')';
            // or output as hex if preferred
        }

        // Hard-code a green-yellow-red colour map for now
        var colourMap = [
            { percentage: 0.0, color: { r: 0x00, g: 0xff, b: 0x00 } },
            { percentage: 0.5, color: { r: 0xff, g: 0xff, b: 0x00 } },
            { percentage: 1.0, color: { r: 0xff, g: 0x00, b: 0x00 } }
        ];

        var range = max - min;
        var magnitude = value - min;
        var percentage = magnitude / range;
        return genColor(percentage, colourMap);
    }

    /**
     * Generate a label for a map item.
     */
    function makeLabel(row) {
        var escapeHTML = (function () {
            'use strict';
            var chr = { '"': '&quot;', '&': '&amp;', '<': '&lt;', '>': '&gt;' };
            return function (text) {
                text = '' + text;
                return text.replace(/[\"&<>]/g, function (a) { return chr[a]; });
            };
        }());
        var label = "";
        for (i in row.values) {
            column = row.columns[i];
            value = row.values[i];
            if (value && column && column.tag != '#geo' && column.tag != '#lat_deg' && column.tag != '#lon_deg' && column.tag != '#x_bounds_js') {
                if (column.header) {
                    label += "    <b>" + escapeHTML(column.header) + ":</b> ";
                } else {
                    label += "    <b>" + escapeHTML(column.tag) + ":</b> ";
                }
                label += escapeHTML(value) + "<br/>\n";
            }
        }
        label += "</dl>";
        return label;
    }

    /**
     * Draw point features on a map.
     */
    function draw_points(hxl) {
        var map_layers = {};

        function get_map_layer(name) {
            if (!map_layers[name]) {
                map_layers[name] = new L.layerGroup();
            }
            return map_layers[name];
        }

        var iterator = hxl.iterator();
        var seen_latlon = false;

        while (row = iterator.next()) {
            var layer = get_map_layer(row.get(params.layer_tag));
            var lat = row.get('#geo+lat') || row.get('#lat_deg');
            var lon = row.get('#geo+lon') || row.get('#lon_deg');
            if (lat != null && !isNaN(lat) && lon != null && !isNaN(lon)) {
                var marker = L.marker([lat, lon]);
                marker.bindPopup(makeLabel(row));
                layer.addLayer(marker);
                seen_latlon = true;
            }
        }

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
    }

    /**
     * Load the HXL and draw the map.
     */
    $('#map-loading').show();
    $.get(params.csv_url, function(csvString) {
        var arrayData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
        var data = hxl.wrap(arrayData);
        // FIXME - for now, always prefer the boundary data to lat/lon
        if (!params.value_tag) {
            params.value_tag = "#meta+count";
        }
        if (params.pcode_tag) {
            var iterator = data.iterator();
            var features = L.featureGroup([]);
            var min_value = data.getMin(params.value_tag);
            var max_value = data.getMax(params.value_tag);

            /**
             * Load boundary object based on pcodes.
             *
             * Uses tail recursion to avoid thread-access problems.
             */
            function load_boundaries(iterator) {
                var row = iterator.next();
                if (!row) {
                    $('#map-loading').hide();
                    map.fitBounds(features.getBounds());
                    return;
                }
                var pcode = row.get(params.pcode_tag);
                if (pcode) {
                    var url = params.pcode_base_url + '/' + params.default_country + '/' + pcode + '/shape.json';
                    $('#map-loading').text(params.pcode_tag + '=' + pcode);
                    jQuery.ajax(url, {
                        success: function (geometry) {
                            var count = row.get(params.value_tag);
                            var label = makeLabel(row);
                            var layer = L.geoJson(geometry, {
                                style: {
                                    color: makeColor(count, min_value, max_value),
                                    opacity: 0.5,
                                    weight: 2
                                }
                            });
                            layer.bindPopup(label);
                            features.addLayer(layer);
                            map.addLayer(features);
                            // tail recursion
                            load_boundaries(iterator);
                        },
                        error: function (xhr, message, exception) {
                            console.log(pcode, url, message, exception);
                            load_boundaries(iterator);
                        }
                    });
                } else {
                    // null value, but keep going
                    load_boundaries(iterator);
                }
            }
            load_boundaries(iterator);
        } else if ((data.hasColumn('#geo+lat') || data.hasColumn('#lat_deg')) && (data.hasColumn('#geo+lon') || data.hasColumn('#lon_deg'))) {
            draw_points(data);
        } else {
            alert("Either #geo+bounds or #geo+lat and #geo+lon needed for a map.");
        }
    }).fail(function () {
        alert("Failed to load dataset " + params.data_url);
        throw "Failed to load dataset " + params.data_url;
    });

    var bounds_cache = {}
    
    var map = L.map('map-div');
    var map_markers = new L.MarkerClusterGroup();

    var osmUrl='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    var osmAttrib='Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
    var osm = new L.TileLayer(osmUrl, {attribution: osmAttrib});
    map.addLayer(osm);
};

hxl_proxy.pad2 = function (num) {
    return ('00' + num).substr(-2);
    var s = num+"";
    while (s.length < size) s = "0" + s;
    return s;
};


/**
 * Parse the name of a sequentially-numbered field
 */
hxl_proxy.parseFieldName = function (name) {

    // try double numbering first
    var result = /^(.+)([0-9][0-9])-([0-9][0-9])$/.exec(name);
    if (result) {
        return [result[1], parseInt(result[2]), parseInt(result[3])]
    }

    // now try single numbering
    result = /^(.+)([0-9][0-9])$/.exec(name);
    if (result) {
        return [result[1], parseInt(result[2])];
    }

    // field is not numbered
    return [name];
};


/**
 * Construct a sequential field name from its parts.
 */
hxl_proxy.makeFieldName = function (parts) {
    var name = parts[0];

    if (parts[1]) {
        name += ('00' + parts[1]).substr(-2);
    }

    if (parts[2]) {
        name += '-' + ('00' + parts[2]).substr(-2);
    }

    return name;
};


/**
 * Add a field in a list.
 */
hxl_proxy.addField = function (contextNode) {
    var lastInputNode = $(contextNode).siblings('input').last();
    var newInputNode = $(lastInputNode).clone();
    var parts = hxl_proxy.parseFieldName($(lastInputNode).attr('name'));
    console.log(parts);
    if (parts[2]) {
        parts[2]++;
        var name = hxl_proxy.makeFieldName(parts);
        $(newInputNode).attr('name', name).attr('value', '').insertAfter(lastInputNode);
    }
};

// end
