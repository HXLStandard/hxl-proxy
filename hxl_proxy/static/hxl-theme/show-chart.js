// Load the Visualization API and the piechart package.
google.load('visualization', '1.0', {'packages':['corechart']});

// Set a callback to run when the Google Visualization API is loaded.
google.setOnLoadCallback(drawChart);

function get_label_tag(hxl) {
    if (chart_label_tag && hxl.hasColumn(chart_label_tag)) {
        return chart_label_tag;
    } else {
        // FIXME - just defaulting to first tag for now
        return hxl.columns[0].tag;
    }
}

function get_value_tag(hxl) {
    if (chart_value_tag && hxl.hasColumn(chart_value_tag)) {
        return chart_value_tag;
    } else {
        for (i in hxl.columns) {
            if (/_num$/.test(hxl.columns[i].tag)) {
                return hxl.columns[i].tag;
            }
        }
        alert("No _num tag available for charting.");
    }
}

// Callback that creates and populates a data table,
// instantiates the pie chart, passes in the data and
// draws it.
function drawChart() {

    $.get(csv_url, function(csvString) {
        var rawData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
        var hxlData = new HXLDataset(rawData);
        var label_tag = get_label_tag(hxlData);
        var value_tag = get_value_tag(hxlData);

        var chartData = [[label_tag, value_tag]];
        var iterator = hxlData.iterator();
        while (row = iterator.next()) {
            var label = row.get(label_tag);
            var value = row.get(value_tag);
            if (!isNaN(value)) {
                chartData.push([label, 0 + value]);
            }
        }

        var data = google.visualization.arrayToDataTable(chartData);

        var options = {
            width: '100%',
            height: '480'
        };

        if (chart_type == 'bar') {
            var chart = new google.visualization.BarChart(document.getElementById('chart_div'));
        } else if (chart_type == 'column') {
            var chart = new google.visualization.ColumnChart(document.getElementById('chart_div'));
        } else {
            if (chart_type && chart_type != 'pie') {
                alert("Unknown chart type: " + chart_type + "\nPlease use 'bar', 'column', or 'pie'");
            }
            var chart = new google.visualization.PieChart(document.getElementById('chart_div'));
        }

        chart.draw(data, options);
    });
}
