AmCharts.shortMonthNames = ['Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru']

var chart2 = AmCharts.makeChart("chart-devices", {
    "type": "serial",
    "theme": "light",
    "legend": {
        "maxColumns": 4,
        "position": "top",
        "useGraphSettings": true,
        "markerSize": 8,
        "valueWidth": 10,
        "equalWidths": true
    },
    "dataLoader": {"url": "/api/device-class/", "format": "json"},
    "valueAxes": [{
        "stackType": "regular",
        "axisAlpha": 0.3,
        "gridAlpha": 0
    }],
    "graphs": [{
        "balloonText": "<b>[[title]]</b><br><span style='font-size:14px'>[[category]]: <b>[[value]]</b></span>",
        "fillAlphas": 0.8,
        "labelText": "[[value]]",
        "lineAlpha": 0.3,
        "title": "Klasa 1",
        "type": "column",
        "valueField": "class1"
    }, {
        "balloonText": "<b>[[title]]</b><br><span style='font-size:14px'>[[category]]: <b>[[value]]</b></span>",
        "fillAlphas": 0.8,
        "labelText": "[[value]]",
        "lineAlpha": 0.3,
        "title": "Klasa 2",
        "type": "column",
        "valueField": "class2"
    }, {
        "balloonText": "<b>[[title]]</b><br><span style='font-size:14px'>[[category]]: <b>[[value]]</b></span>",
        "fillAlphas": 0.8,
        "labelText": "[[value]]",
        "lineAlpha": 0.3,
        "title": "Klasa 3",
        "type": "column",
        "valueField": "class3"
    }, {
        "balloonText": "<b>[[title]]</b><br><span style='font-size:14px'>[[category]]: <b>[[value]]</b></span>",
        "fillAlphas": 0.8,
        "labelText": "[[value]]",
        "lineAlpha": 0.3,
        "title": "Klasa 4",
        "type": "column",
        "valueField": "class4"
    }],
    "categoryField": "year",
    "categoryAxis": {
        "gridPosition": "start", "axisAlpha": 0, "gridAlpha": 0, "position": "bottom"
    },
    "export": {"enabled": true}
});