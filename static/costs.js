$(document).ready(function () {
    bindDataTables();
});

function showCostsLayer(devicesId) {

    var url = '/koszty/zakres?device_id=' + devicesId
    $.get(url, function (data) {
        $.fancybox(data);
    });

}

function bindDataTables() {
    oTable = $('#device_table').dataTable({
        'sPaginationType': 'full_numbers',
        "bJQueryUI": true,
        'sDom': '<"H"<"arrow">TRCflr>t<"F"ip>',
        "oTableTools": {
            "sSwfPath": "/site_media/DataTables-1.9.1/extras/TableTools/media/swf/copy_csv_xls_pdf.swf",
            "aButtons": [
                {
                    "sExtends": "select",
                    "sButtonText": "Koszty",
                    "fnClick": function (nButton, oConfig, oFlash) {
                        devicesId = [];
                        $("#device_table tbody input:checked").each(function (index) {
                            var id = $(this).val();
                            devicesId.push(id);
                        });
                        if (devicesId.length > 0) {
                            showCostsLayer(devicesId);
                        } else {
                            alert("Proszę wybrać jedno urządzenie");
                            return false;
                        }
                    }
                },

            ]
        },
        "bSaveState": true,
        "bAutoWidth": false,
        "oColVis": {"aiExclude": [ 0 ], "sSize": "css", "buttonText": "Wybór kolumn", "bRestore": true, "sRestore": "<b>Resetuj kolumny</b>"},
        "oLanguage": {
            "sEmptyTable": "Brak danych do wyświetlenia",
            "sSearch": "szukaj:",
            "sLengthMenu": "Pokaż _MENU_ wyników",
            "sInfo": "wyniki: _START_ - _END_ z _TOTAL_",
            "oPaginate": {
                "sFirst": "&laquo;",
                "sPrevious": "&lsaquo;",
                "sLast": "&raquo;",
                "sNext": "&rsaquo;"
            }
        },
        "aaSorting": [[ 1, "desc" ]], // sort by id/lp
		"aoColumns": [
            {
                "mDataProp": "id",
//                "fnRender": function ( oObj ) {
//
//                    var checked_str = "";
//                    var _sd = localStorage.selected_devices;
//                    if (_sd) {
//                        _sd = JSON.parse(_sd);
//                        if (_sd.hasOwnProperty(oObj.aData.id)) checked_str = " checked=\"checked\" ";
//                    }
//
//                    return '<input type=\"checkbox\"' + checked_str + 'id=\"sel'+ oObj.aData["id"] +'\" value="'+ oObj.aData["id"] +'"> ';
//                },
                "aTargets": [ 0 ],
                "bSortable": false, "sWidth": "1%"
            },
			{ "mDataProp": "lp", "bSearchable": true, "sWidth": "1%"}, // lp
			{ "mDataProp": "name", "bSearchable": true, "sWidth": "15%"}, // nazwa
			{ "mDataProp": "genre", "bSearchable": true, "sWidth": "8%"}, // rodzaj
			{ "mDataProp": "model", "bSearchable": true, "sWidth": "8%"}, // model
			{ "mDataProp": "make", "bSearchable": true, "sWidth": "8%"}, // producent
			{ "mDataProp": "serial_number", "bSearchable": true, "sWidth": "10%"}, // nr seryjny
			{ "mDataProp": "inventory_number", "bSearchable": true, "sWidth": "10%"}, // nr inwentarzowy
			{ "mDataProp": "location", "bSearchable": true, "sWidth": "8%"}, // lokalizacja
            { "mDataProp": "location_place", "bSearchable": true, "sWidth": "8%"}, // lokalizacja miejsce
			{ "mDataProp": "person_responsible", "bSearchable": true, "sWidth": "8%"}, // osoba odpowiedzialna
			{ "mDataProp": "technical_supervisor", "bSearchable": true, "sWidth": "8%"}, // nadzor techniczny
			{ "mDataProp": "status", "bSearchable": true, "sWidth": "6%"}, // status
            { "mDataProp": "date_warranty", "bSearchable": true, "sWidth": "6%"} // date_warranty
		],
        "fnInitComplete": function(oSettings, json) {


            $(oSettings.nTable).find("thead").append("<tr></tr>");
            for (c = 0; c<oSettings.aoColumns.length; c++) {
                if (c==0 || c==100) {
                    $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td id=\"device-selection-info\">&nbsp;</td>");
                } else {
                    var _class = (oSettings.aoColumns[c].bVisible) ? "" : " class=\"hidden\"";
                    $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td" + _class + "><input name=\"search_" + oSettings.aoColumns[c]["mDataProp"] + "\" type=\"text\" value=\"" + oSettings.aoPreSearchCols[c].sSearch + "\" /></td>");
                }
            }
            $(oSettings.nTable).find("thead input").keyup(function() {
                oTable.fnFilter( this.value, oTable.oApi._fnVisibleToColumnIndex( oTable.fnSettings(), $("#devices-table thead input").index(this) ) ); // TODO wlasna funkcja do mapowania aktualnej kolumny do wlasciwej (mDataProp) - czy aby na pewno potrzebna?
            });
        },

    });
}
