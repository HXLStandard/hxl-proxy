/**
 * Root object for all HXL Proxy functions and variables.
 */
var hxl_proxy = {}

hxl_proxy.prepare_form = function() {

    function setup_fieldset(node, index) {
        filter_name = $(node).find(".field_filter select").val();
        filter_class = ".fields-" + filter_name;
        filter_title = "" + (index + 1) + ": " + (filter_name ? filter_name : '(not set)');
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


hxl_proxy.setupChart = function(params) {

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

        function get_value_pattern(hxl) {
            if (params.value_pattern && hxl.hasColumn(params.value_pattern)) {
                return params.value_pattern;
            } else {
                for (i in hxl.columns) {
                    if (hxl.columns[i].tag == '#meta+count' || /_num$/.test(hxl.columns[i].tag)) {
                        return hxl.columns[i].tag;
                    }
                }
                alert("Can't guess numeric column for charting.");
            }
        }

        $.get(params.data_url, function(csvString) {
            var rawData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
            var hxlData = new HXLDataset(rawData);
            var label_pattern = get_label_pattern(hxlData);
            var value_pattern = get_value_pattern(hxlData);

            var chartData = [[label_pattern, value_pattern]];
            var iterator = hxlData.iterator();
            while (row = iterator.next()) {
                var label = row.get(label_pattern);
                var value = row.get(value_pattern);
                if (!isNaN(value)) {
                    chartData.push([label, 0 + value]);
                }
            }

            var data = google.visualization.arrayToDataTable(chartData);

            var options = {
                width: '100%',
                height: '480'
            };

            if (params.type == 'bar') {
                var chart = new google.visualization.BarChart(document.getElementById('chart_div'));
            } else if (params.type == 'column') {
                var chart = new google.visualization.ColumnChart(document.getElementById('chart_div'));
            } else {
                if (params.type && params.type != 'pie') {
                    alert("Unknown chart type: " + params.type + "\nPlease use 'bar', 'column', or 'pie'");
                }
                var chart = new google.visualization.PieChart(document.getElementById('chart_div'));
            }

            chart.draw(data, options);
        });
    }

    // Load the Visualization API and the piechart package.
    google.load('visualization', '1.0', {'packages':['corechart']});

    // Set a callback to run when the Google Visualization API is loaded.
    google.setOnLoadCallback(drawChart);

};

