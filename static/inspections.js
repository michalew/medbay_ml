$(document).ready(function() {
    $("[name^='search']").val("")

    $("#inspections-table thead #selall").click(function() {
        var _checked = $(this).prop("checked");
        $("#inspections-table tbody input:checkbox").prop("checked", _checked).each(function() {
            var _id = $(this).attr("id");
            var inspection_id = _id.replace("sel", "");

            var _sd = localStorage.selected_inspections;
            if (_sd) _sd = JSON.parse(_sd)
            else _sd = new Object()

            if (_checked && !_sd[inspection_id]) _sd[inspection_id]= _id;
            else delete(_sd[inspection_id]);
            localStorage.selected_inspections = JSON.stringify(_sd);
        });

    });

});

function print_inspection_table(){
    var ids = []
    $("#inspections-table tbody input:checked").each(function(index) { var id = $(this).val(); ids.push(id); });

    if (ids.length > 0) {
        generate_pdf_directly("all_table", ids);
    } else {
        alert("Proszę wybrać conajmniej jedno urządzenie"); return false;
    }
}

function clear_columns_filter(oTable){
    oTable.fnFilter('');
    $("[name^='search']").val("")
      var oSettings = oTable.fnSettings();
      for(iCol = 0; iCol < oSettings.aoPreSearchCols.length; iCol++) {
        oSettings.aoPreSearchCols[ iCol ].sSearch = '';
      }
      oTable.fnDraw();
}

function add_inspections(){
    if (typeof(window.return_inspection_devices) !== 'undefined' && window.return_inspection_devices) {
        var devices = window.return_inspection_devices;
    } else {
        var devices = "";
    }

    $.get("/przeglady/nowy?devices=" + devices, function(data) {
        $.fancybox(
            data,
            {
                'onClosed': function() {

                },
                'onCleanup': function() {
                    //oTable.fnDraw(false);
                }
            }
        );
    });
}

function print_inspectionplan_table(rows, titles){
    if (rows.length > 0) {
        generate_pdf_directly("inspection_plan_table", rows, titles);
    } else {
        alert("Proszę wybrać conajmniej jeden plan przeglądu"); return false;
    }
}

function load_inspections() { // funkcja buduje tabelke z urzadzeniami
    /* Add the events etc before DataTables hides a column */

    $("#inspections-table thead input").keyup( function () {
        oTableInspection.fnFilter(
            this.value,
            oTableInspection.oApi._fnVisibleToColumnIndex( oTableInspection.fnSettings(), $("#inspections-table thead input").index(this) )
        );
    });
	oTableInspection = $('#inspections-table').dataTable({ // init the inspections table
		'sPaginationType': 'full_numbers', 
		"bServerSide": true, 
        "bJQueryUI": true,
        'sDom': '<"H"<>TRCfr>t<"F"ilp>',
        "bSort": true,
        "oTableTools": {
            "sSwfPath": "/site_media/DataTables-1.9.1/extras/TableTools/media/swf/copy_csv_xls_pdf.swf",
            "aButtons": [
                {
                    "sExtends":    "select",
                    "sButtonText": "Dodaj przegląd/konserwację",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        add_inspections();
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "Edytuj przeglądy/konserwacje",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        location.href = "/a/cmms/inspection/"
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "Eksportuj do XLS",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        inspections_ids = [];
                        $("#inspections-table tbody input:checked").each(function(){
                          $(this).parents('tr').find("td").each(function(){
                                inspections_ids.push($(this).text());
                          });
                          inspections_ids.push("<SEP>")
                        });
                        if (inspections_ids.length > 0) { generate_xls('InspectionPlan', inspections_ids); } else { alert("Proszę wybrać przynajmniej jeden przegląd"); return false; }
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "PDF",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        var inspections_ids = [];
                        $("#inspections-table tbody input:checked").each(function(){
                          $(this).parents('tr').find("td").each(function(){
                                inspections_ids.push($(this).text());
                          });
                          inspections_ids.push("<SEP>");
                        });
                        var titles = [];
                        $("#inspections-table").find("thead th").each(function(){
                            titles.push($(this).text());
                        });
                        print_inspectionplan_table(inspections_ids, titles);
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "Czyść filtr kolumnowy",
                    "sButtonClass": "clear-filter",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        clear_columns_filter(oTableInspection);

                    }
                },
            ]
        },
        "bStateSave": true,
            "fnStateSave": function (oSettings, oData) {
            localStorage.setItem( 'DataTables', JSON.stringify(oData) );
        },
        "fnStateLoad": function (oSettings) {
            return JSON.parse( localStorage.getItem('DataTables') );
        },
        "bAutoWidth": false,
		"sAjaxSource": '/ajax/inspections/',
		"oColVis": {"aiExclude": [ 0 ], "sSize": "css", "buttonText": "Wybór kolumn", "bRestore": true, "sRestore": "<b>Resetuj kolumny</b>", "fnStateChange": function ( iColumn, bVisible ) {
            $("#inspections-table thead tr:last-child td:nth-child(" + (iColumn + 1) + ")").toggleClass("hidden", !bVisible);
        }},
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
                "fnRender": function ( oObj ) {

                    var checked_str = "";
                    var _sd = localStorage.selected_inspections;
                    if (_sd) {
                        _sd = JSON.parse(_sd);
                        if (_sd.hasOwnProperty(oObj.aData.id)) checked_str = " checked=\"checked\" ";
                    }

                    return '<input type=\"checkbox\"' + checked_str + 'id=\"sel'+ oObj.aData["id"] +'\" value="'+ oObj.aData["id"] +'"> ';
                    //return o.aData[0] +' '+ o.aData[3];
                },
                "aTargets": [ 0 ],
                "bSortable": false, "sWidth": "1%"
            },
            { "mDataProp": "from_which_inspection", "bSearchable": true, "sWidth": "1%"}, // inspection ID
            { "mDataProp": "lp_device", "bSearchable": true, "sWidth": "1%"}, // lp
			{ "mDataProp": "name", "bSearchable": true, "sWidth": "15%"}, // nazwa
            { "mDataProp": "make", "bSearchable": true, "sWidth": "8%"}, // producent
			{ "mDataProp": "model", "bSearchable": true, "sWidth": "8%"}, // model
			{ "mDataProp": "serial_number", "bSearchable": true, "sWidth": "10%"}, // nr seryjny
			{ "mDataProp": "inventory_number", "bSearchable": true, "sWidth": "10%"}, // nr inwentarzowy
			{ "mDataProp": "location", "bSearchable": true, "sWidth": "8%"}, // lokalizacja
            { "mDataProp": "ticket_id", "bSearchable": true, "sWidth": "8%"}, // id zgłoszenia
			{ "mDataProp": "inspection_type", "bSearchable": true, "sWidth": "8%"}, // typ przeglądu
			{ "mDataProp": "planned_date_execute", "bSearchable": true, "sWidth": "8%"}, // planowana data wykonania
			{ "mDataProp": "date_execute", "bSearchable": true, "sWidth": "6%"}, // data wykonania
            { "mDataProp": "person_execute", "bSearchable": true, "sWidth": "6%"}, // wykonawca
            { "mDataProp": "contractor_execute", "bSearchable": true, "sWidth": "6%"}, // wykonawca firma
            { "mDataProp": "description", "bSearchable": true, "sWidth": "6%"} // uwagi
		],
        "fnInitComplete": function(oSettings, json) {
            if (blink) {
                $("#ToolTables_devices-table_0").css({'font-weight': 'bold'});
                $(oSettings.nTable).find("td:first-child").each(function () {
                    checkbox = $(this).find("input");
                });
                blink = false;
            }

            $(oSettings.nTable).find("thead").append("<tr></tr>");
            for (c = 0; c<oSettings.aoColumns.length; c++) {
                if (c==0 || c==100) {
                    $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td>&nbsp;</td>");
                } else {
                    var _class = (oSettings.aoColumns[c].bVisible) ? "" : " class=\"hidden\"";
                    $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td" + _class + "><input name=\"search_" + oSettings.aoColumns[c]["mDataProp"] + "\" type=\"text\" value=\"" + oSettings.aoPreSearchCols[c].sSearch + "\" /></td>");
                }
            }
            $(oSettings.nTable).find("thead input").keyup(function() {
                oTableInspection.fnFilter( this.value, oTableInspection.oApi._fnVisibleToColumnIndex(oTableInspection.fnSettings(), $("#inspections-table thead td:not(.hidden) input").index(this) +1)); // TODO wlasna funkcja do mapowania aktualnej kolumny do wlasciwej (mDataProp) - czy aby na pewno potrzebna?
            });
        },
        "fnDrawCallback": handle_checkall
	});
}

function handle_checkall() {
    var checked_count = $("#inspections-table tbody input:checked").length;
    var rows_count = $("#inspections-table tbody tr").length;
    if ( checked_count < rows_count ) $("#inspections-table thead #selall").prop("checked", false);
    if ( checked_count == rows_count ) $("#inspections-table thead #selall").prop("checked", true);
}
