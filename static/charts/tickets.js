AmCharts.shortMonthNames = ['Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru']

var chart = AmCharts.makeChart("chart-tickets", {
    "type": "serial",
    "theme": "light",
    "dataLoader": {"url": "/api/ticket-graph/", "format": "json"},
    "valueAxes": [{
        "gridColor": "#FFFFFF",
        "gridAlpha": 0.2,
        "dashLength": 0
    }],
    "gridAboveGraphs": true,
    "startDuration": 1,
    "graphs": [{
        "id": "g1",
        "balloonText": "[[category]]: <b>[[value]]</b>",
        "fillAlphas": 0.8,
        "lineAlpha": 0.2,
        "type": "column",
        "valueField": "tickets"
    }],
    "chartScrollbar": {
        "graph": "g1",
        "oppositeAxis": false,
        "offset": 30,
        "scrollbarHeight": 80,
        "backgroundAlpha": 0,
        "selectedBackgroundAlpha": 0.1,
        "selectedBackgroundColor": "#888888",
        "graphFillAlpha": 0,
        "graphLineAlpha": 0.5,
        "selectedGraphFillAlpha": 0,
        "selectedGraphLineAlpha": 1,
        "autoGridCount": true,
        "color": "#AAAAAA"
    },
    "chartCursor": {
        "categoryBalloonEnabled": false,
        "cursorAlpha": 0,
        "zoomable": false
    },
    "categoryField": "day",
    "categoryAxis": {
        "gridPosition": "start",
        "gridAlpha": 0,
        "tickPosition": "start",
        "tickLength": 20,
        "parseDates": true
    },
    "dataDateFormat": "DD-MM-YYYY",
    "equalSpacing": true,
    "export": {"enabled": true},
});
chart.addListener("rendered", zoomChart);
zoomChart();
function zoomChart() {
    var today = new Date()
    var priorDate = new Date().setDate(today.getDate() - 30)
    chart.zoom(priorDate, today);
}