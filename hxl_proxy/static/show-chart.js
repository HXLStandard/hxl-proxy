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
        //view.setColumns([0,1]);

        options = {
            title: "",
            width: '100%',
            height: 600,
            legend: {'position': 'none'},
            bar: {groupWidth: "95%"},
            hAxis: {
                title: data.getColumnLabel(0),
                type: 'string'
            },
            vAxis: {
                title: data.getColumnLabel(1),
                minValue: data.getColumnRange(1).min,
                maxValue: data.getColumnRange(1).max,
                type: 'number'
            }
        };

        // Instantiate and draw our chart, passing in some options.
        node = document.getElementById('chart_div');
        if (chart_type == 'bar') {
            var chart = new google.visualization.BarChart(node);
        } else if (chart_type == 'column') {
            var chart = new google.visualization.ColumnChart(node);
        } else {
            var chart = new google.visualization.PieChart(node);
        }
        chart.draw(view, options);
    });

}
