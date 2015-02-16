// Load the Visualization API and the piechart package.
google.load('visualization', '1.0', {'packages':['corechart']});

// Set a callback to run when the Google Visualization API is loaded.
google.setOnLoadCallback(drawChart);

// Callback that creates and populates a data table,
// instantiates the pie chart, passes in the data and
// draws it.
function drawChart() {

    $.get(csv_url, function(csvString) {
        var arrayData = $.csv.toArrays(csvString, {onParseValue: $.csv.hooks.castToScalar});
        arrayData.shift();
        var data = new google.visualization.arrayToDataTable(arrayData);
        var view = new google.visualization.DataView(data);
        view.setColumns([0,1]);

        options = {
            hAxis: {title: data.getColumnLabel(0), minValue: data.getColumnRange(0).min, maxValue: data.getColumnRange(0).max},
            vAxis: {title: data.getColumnLabel(1), minValue: data.getColumnRange(1).min, maxValue: data.getColumnRange(1).max},
            chartArea: { left: 0, top: 0, height: 600, width: 600 }
        };

        // Instantiate and draw our chart, passing in some options.
        var chart = new google.visualization.PieChart(document.getElementById('chart_div'));
        chart.draw(view, options);
    });

}
