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


////////////////////////////////////////////////////////////////////////
// File choosers for cloud services.
//
// Callbacks for choosing a file from an external service.
////////////////////////////////////////////////////////////////////////

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
        var url = 'https://data.humdata.org/dataset/' + resource.package_id + '/resource/' + resource.id
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


////////////////////////////////////////////////////////////////////////
// User-interface functions.
//
// Functions for manipulating the DOM or responding to user actions.
////////////////////////////////////////////////////////////////////////


hxl_proxy.ui = {};


/**
 * Set up the forms for recipe filters.
 *
 * @param form_node The node of the <form> element containing the filters.
 */
hxl_proxy.ui.setup_filters = function (form_node) {

    /**
     * Set up the form for a single recipe filter.
     */
    function setup_filter_form(node, index) {
        var field_types = "input,select,textarea"

        // Grab info from the (possibly hidden) select element
        var filter_name = $(node).find(".field_filter select").val();
        var filter_desc = $(node).find(".field_filter option:selected").text();
        var filter_class = ".filter-" + filter_name;

        // Hide all filters, then show the currently-chosen one
        $(node).find(".filter-body").hide();
        $(node).find(".filter-body").find(field_types).prop("disabled", true);
        $(node).find(filter_class).show();
        $(node).find(filter_class).find(field_types).prop("disabled", false);
    };

    // Set up the new-filter form on the recipe page
    $(form_node).find(".filter-new").each(function (index) {
        var filter_node = this;
        setup_filter_form(filter_node, index);
        // Reconfigure form view when the type selector changes
        $(filter_node).find(".field_filter select").on("change", function () {
            setup_filter_form(filter_node, index);
        })
    });

    // Set up aggregate fields for the count filter
    $(form_node).find(".filter-count .aggregate").each(function (index) {
        function setup (container_node, select_node) {
            var aggregate_type = select_node.val();
            var header_node, column_node;
            if (!aggregate_type) {
                container_node.find('.aggregate-pattern').hide().find('input').attr('required', false);
                header_node = container_node.find('.aggregate-header').hide().find('input');
                column_node = container_node.find('.aggregate-column').hide().find('input').attr('required', false);
            } else if (aggregate_type == 'count') {
                container_node.find('.aggregate-pattern').hide().find('input').attr('required', false);
                header_node = container_node.find('.aggregate-header').show().find('input');
                column_node = container_node.find('.aggregate-column').show().find('input').attr('required', true);
            } else {
                var title = aggregate_type.slice(0, 1).toUpperCase() + aggregate_type.slice(1);
                container_node.find('.aggregate-pattern').show().find('input').attr('required', true);
                header_node = container_node.find('.aggregate-header').show().find('input');
                column_node = container_node.find('.aggregate-column').show().find('input').attr('required', true);
            }
            // provide default values, if needed
            if (aggregate_type) {
                var title = aggregate_type.slice(0, 1).toUpperCase() + aggregate_type.slice(1);
                if (!header_node.attr('value')) {
                    header_node.attr('value', title);
                }
                if (!column_node.attr('value')) {
                    column_node.attr('value', '#meta+' + aggregate_type);
                }
            }
        }
        var container_node = $(this);
        var select_node = container_node.find('select');
        setup(container_node, select_node);
        select_node.on("change", function (event) {
            setup(container_node, select_node);
            return true;
        });
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
            alert("Please use the customise button to set up the map.");
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


/**
 * Trim empty fields from a form before submitting.
 * TODO: needs to be able to handle failed validation.
 */
hxl_proxy.ui.trimForm = function (contextNode) {
    $(contextNode).find(":input").filter(function () {
        return !this.value;
    }).attr("disabled", "disabled");
    return true; // ensure form still submits
};


/**
 * Trim unused fields from the tagger.
 */
hxl_proxy.ui.trimTagger = function (formNode) {
    for (var i = 1; i < 100; i++) {
        var baseName = "tagger-" + hxl_proxy.util.pad2(i);
        var headerNode = $(formNode).find("input[name='" + baseName + "-header']");
        var tagNode = $(formNode).find("input[name='" + baseName + "-tag']");
        if (!tagNode.val()) {
            headerNode.attr("disabled", "disabled");
            tagNode.attr("disabled", "disabled");
        }
    }
    return true;
};


/**
 * Add a field in a list.
 */
hxl_proxy.ui.addField = function (contextNode) {
    var lastInputNode = $(contextNode).siblings('input').last();
    var newInputNode = $(lastInputNode).clone(true);
    var parts = hxl_proxy.util.parseFieldName($(lastInputNode).attr('name'));
    if (parts[2]) {
        parts[2]++;
        var name = hxl_proxy.util.makeFieldName(parts);
        $(newInputNode).attr('name', name).attr('value', '').insertAfter(lastInputNode);
    }
};


/**
 * Event handler: renumber HTML markup for a filter list and submit.
 * Event handler for the sortable JS library.
 */
hxl_proxy.ui.resortFilterForms = function (event, ui) {
    $(event.target.childNodes).filter('.filter').each(hxl_proxy.ui.renumberFilterForm);
    $(event.target.childNodes).closest('form').submit();
};


/**
 * Renumber HTML markup for a filter form (including all fields).
 * @param index The zero-based index in the new order (will be converted to 1-based).
 * @param filterNode The root node of the tree to renumber.
 */
hxl_proxy.ui.renumberFilterForm = function (index, filterNode) {
    $(filterNode).find('*').each(function (i, formNode) {
        $.each(['name', 'for', 'id'], function (i, name) {
            var oldValue = $(formNode).attr(name);
            if (oldValue) {
                var newValue = oldValue.replace(/\d\d/, hxl_proxy.util.pad2(index + 1));
                if (oldValue != newValue) {
                    $(formNode).attr(name, newValue);
                }
            }
        });
    });
};


/**
 * Remove a filter from the form.
 */
hxl_proxy.ui.removeFilter = function (node) {
    if (confirm("Remove filter?")) {
        var form = $(node).closest('form');
        $(node).closest("li").remove();
        form.find('.filter').each(hxl_proxy.ui.renumberFilterForm);
        form.submit();
    }
    return false;
};


/**
 * Renumber subitems in a form section.
 * @param container: The container node
 * @param selector: The selector for the items to renumber.
 */
hxl_proxy.ui.renumberFormItems = function (container, selector) {
    // Form attributes to be renumbered
    var atts = ['id', 'name', 'for'];

    // Iterate over just the items to get the count
    $(container).find(selector).each(function (index, item) {

        // Renumber everything inside each item with the item number (+1)
        $(item).find('*').addBack().each(function (i, node) {
            for (i in atts) {
                var name = atts[i];
                var value = $(node).attr(name);
                if (value && value.match(/-[0-9][0-9]$/)) {
                    var parts = hxl_proxy.util.parseFieldName(value);
                    $(node).attr(name, hxl_proxy.util.makeFieldName([parts[0], parts[1], index + 1]));
                }
            }
        });
    });
};


/**
 * Duplicate a form item (repeatable field or section).
 * @param node The node to duplicate (new copy will be right after).
 * @param container_selector JQuery selector for the container node.
 * @param item_selector JQuery selector for the repeatable items (usually a class).
 */
hxl_proxy.ui.duplicate = function (node, container_selector, item_selector) {
    var new_node = $(node).clone();
    $(new_node).find('input[value],textarea[value]').attr('value', '');
    $(node).after(new_node);
    hxl_proxy.ui.renumberFormItems($(node).closest(container_selector), item_selector);
    hxl_proxy.ui.setup_filters($(node).closest('form'));
};


/**
 * Delete a form item (repeatable field or section).
 * @param node The node to delete.
 * @param container_selector JQuery selector for the container node.
 * @param item_selector JQuery selector for the repeatable items (usually a class)
 */
hxl_proxy.ui.delete = function (node, container_selector, item_selector) {
    var container = $(node).closest(container_selector);
    if ($(container).find(item_selector).length > 1) {
        if (confirm("Remove item?")) {
            $(node).remove();
            hxl_proxy.ui.renumberFormItems(container, item_selector);
        }
    } else {
        alert("Can't remove last item.");
    }
};


////////////////////////////////////////////////////////////////////////
// Utility functions.
////////////////////////////////////////////////////////////////////////


hxl_proxy.util = {};


/**
 * Left 0-pad an integer to two places.
 * @param num The integer to pad.
 * @return Two-character string representation, zero-padded.
 */
hxl_proxy.util.pad2 = function (num) {
    return ('00' + num).substr(-2);
    var s = num+"";
    while (s.length < size) s = "0" + s;
    return s;
};


/**
 * Parse the name of a sequentially-numbered field
 */
hxl_proxy.util.parseFieldName = function (name) {

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
hxl_proxy.util.makeFieldName = function (parts) {
    var name = parts[0];

    if (parts[1]) {
        name += hxl_proxy.util.pad2(parts[1]);
    }

    if (parts[2]) {
        name += '-' + hxl_proxy.util.pad2(parts[2]);
    }

    return name;
};


////////////////////////////////////////////////////////////////////////
// Run startup code.
////////////////////////////////////////////////////////////////////////


// For all forms with the class "autotrim", disable any fields with empty values
$(function() {
    $("form.autotrim").submit(function() {
        $(this).find(":input").filter(function(){ return !this.value; }).attr("disabled", "disabled");
        return true; // ensure form still submits
    });
});


// Trim empty elements from forms on submission.
$(function() {
    $("form").submit(function() { hxl_proxy.ui.trimForm(this); });
});


// Trim unused rows from the tagger form
$(function() {
    $("form.tagger").submit(function () { hxl_proxy.ui.trimTagger(this); });
});


// end
