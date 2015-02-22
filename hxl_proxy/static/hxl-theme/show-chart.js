// Load the Visualization API and the piechart package.
google.load('visualization', '1.0', {'packages':['corechart']});

// Set a callback to run when the Google Visualization API is loaded.
google.setOnLoadCallback(drawChart);

// Callback that creates and populates a data table,
// instantiates the pie chart, passes in the data and
// draws it.
function drawChart() {

    $.get(csv_url, function(csvString) {
        var rawData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
        var hxlData = new HXLDataset(rawData);

        var chartData = [[chart_label_tag, chart_value_tag]];
        var iterator = hxlData.iterator();
        while (row = iterator.next()) {
            var label = row.get(chart_label_tag);
            var value = row.get(chart_value_tag);
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
