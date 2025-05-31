var single_item = false;

if (typeof single_device !== 'undefined' && objects_name=='device') {
    single_item = true;
}

$(document).ready(function(){
    $(".filter-objects").click(function(event){
        event.preventDefault();
        window.LAST_INSPECTION_DATA = {};
        $("#add-inspection input").each(function(){
           var name = $(this).attr("name");
           var value = $(this).val();
           window.LAST_INSPECTION_DATA[name] = value
        });
        $("#add-inspection select").each(function(){
            var name = $(this).attr("name");
            var value = $(this).val();
            window.LAST_INSPECTION_DATA[name] = value
        });
        $("#add-inspection textarea").each(function(){
            var name = $(this).attr("name");
            var value = $(this).val();
            window.LAST_INSPECTION_DATA[name] = value
        });

        window.LAST_DATA_FILTER = {};

        $("[id$='_operator']").each(function(){
           var name_operator = $(this).attr("name");
           var name_field = name_operator.split("_operator")[0];
           window.LAST_DATA_FILTER[name_operator] = $(this).val();
           if (name_field != 'device' && name_field != 'service' && name_field != 'ticket')
           window.LAST_DATA_FILTER[name_field] = $("#id_"+name_field).val();
            window.LAST_DATA_FILTER[name_field+"_from"] = $("#id_"+name_field+"_from").val();
            window.LAST_DATA_FILTER[name_field+"_to"] = $("#id_"+name_field+"_to").val();
        });

        is_list = $(this).data("is_list");
        objects_name = $(this).data("objects_name");

        if (objects_name=='ticket'){
          window.object_filter_is_ticket = true;
        }

        if (objects_name=='device'){
          window.object_filter_is_device = true;
        }

        if (objects_name=='service'){
          window.object_filter_is_service = true;
        }

        selected_objs = $(this).parent().find(".current_related_objects_" + objects_name).find("td");
        custom_ticket_filter_selected_ids = window.custom_ticket_filter_m2m_id;
        custom_device_filter_selected_ids = window.custom_device_filter_m2m_id;
        custom_service_filter_selected_ids = window.custom_service_filter_m2m_id;
        current_list_name = $(this).data("current_list_name");

        if (typeof(objects_name) != 'undefined') {
            $.get("/get_filter_"+objects_name+"s", function(data) {
                $.fancybox(data, {
                    'onClosed': function(){
                        $(".edit_button").click();
                        $("#advanced_filter").click();
                        if ( (typeof(IS_INSPECTION_PAGE) !== 'undefined') && IS_INSPECTION_PAGE) {
                            add_inspections();
                        }
                    }
                });

            });
        }
        selected_id = []
    });

    window.redirect = function(url){
        window.location.href = url;
    }



    $(".check_all").click(function() {        
        var table_id = $(this).parents("table").attr("id");
        var is_checked = $(this).prop("checked");
        $("#" + table_id + " tbody input:checkbox").prop("checked", is_checked);
        $("#" + table_id + " tbody input:checkbox").each(function(){
           var val = $(this).val();
           var index_selected_id = selected_id.indexOf(val);
           if ( index_selected_id == -1 && is_checked == true) {
                selected_id.push(val);
           } else if ( index_selected_id != -1 && is_checked == false) {
               selected_id.splice(index_selected_id, 1);

           }
        });
    });
});

function refresh_checked_objects(){
    $("input[id^='sel']").click(function(){
        var val = $(this).val();
        var index_selected_id = selected_id.indexOf(val);
        if ( index_selected_id == -1) {
            selected_id.push(val);
        } else {
            selected_id.splice(index_selected_id, 1);
        }
    });

    if (selected_objs.length != 0) {
        selected_objs.each(function(){
            var id = $(this).prop("id");
            if (id != "" && selected_id.indexOf(id) == -1) {
                selected_id.push(id);
            }
        });
    }
    selected_objs = [];
    var advanced_filter_ids = [];
    if (custom_ticket_filter_selected_ids && custom_ticket_filter_selected_ids.length != 0 && objects_name == 'ticket') {
        var ids = custom_ticket_filter_selected_ids.split(",");
        for (id in ids) {
            if (id != "" && selected_id.indexOf(ids[id]) == -1) {
                selected_id.push(ids[id]);
                advanced_filter_ids.push(ids[id]);
            }
        }

        for (var id in advanced_filter_ids) {
            $("#filter-"+objects_name+"s-table").find("#sel" + advanced_filter_ids[id]).attr("checked", 'checked');
        }
    }

    var advanced_filter_ids = [];
    if (custom_device_filter_selected_ids && custom_device_filter_selected_ids.length != 0 && objects_name == 'device') {
        var ids = custom_device_filter_selected_ids.split(",");
        for (id in ids) {
            if (id != "" && selected_id.indexOf(ids[id]) == -1) {
                selected_id.push(ids[id]);
                advanced_filter_ids.push(ids[id]);
            }
        }

        for (var id in advanced_filter_ids) {
            $("#filter-"+objects_name+"s-table").find("#sel" + advanced_filter_ids[id]).attr("checked", 'checked');
        }
    }

    var advanced_filter_ids = [];
    if (custom_service_filter_selected_ids && custom_service_filter_selected_ids.length != 0 && objects_name == 'external_service') {
        var ids = custom_service_filter_selected_ids.split(",");
        for (id in ids) {
            if (id != "" && selected_id.indexOf(ids[id]) == -1) {
                selected_id.push(ids[id]);
                advanced_filter_ids.push(ids[id]);
            }
        }

        for (var id in advanced_filter_ids) {
            $("#filter-"+objects_name+"s-table").find("#sel" + advanced_filter_ids[id]).attr("checked", 'checked');
        }
    }


    for (var id in selected_id) {
        $("#filter-"+objects_name+"s-table").find("#sel" + selected_id[id]).attr("checked", 'checked');
    }

    custom_ticket_filter_selected_ids = [];
    custom_device_filter_selected_ids = [];
    custom_service_filter_selected_ids = [];

    var all_checked = true
    $("#filter-" + objects_name +"s-table tbody input:checkbox").each(function(){
        if (!$(this).prop("checked")){
            all_checked = false;
        }
    });

    $("#filter-" + objects_name +"s-table .check_all").prop("checked", all_checked)
}

function load_filter_devices(m2m_object_name) { // funkcja buduje tabelke z urzadzeniami
    $("input[name='device']").remove();
    /* Add the events etc before DataTables hides a column */
    $("#filter-devices-table thead input").keyup( function () {
        oTable.fnFilter( this.value, oTable.oApi._fnVisibleToColumnIndex( oTable.fnSettings(), $("#filter-devices-table thead input").index(this) ) );
    } );
	oTable = $('#filter-devices-table').dataTable({
		'sPaginationType': 'full_numbers',
		"bServerSide": true,
        "bJQueryUI": true,
        'sDom': '<"H"<"arrow">TRCflr>t<"F"ip>',
        "oTableTools": {
            "sSwfPath": "/site_media/DataTables-1.9.1/extras/TableTools/media/swf/copy_csv_xls_pdf.swf",
            "aButtons": [
                {
                    "sExtends":    "select",
                    "sButtonText": "OK",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        var selected_id_str = "";
                        var custom_device_filter_m2m_id = "";
                            for (var obj in selected_id) {
                                selected_id_str += selected_id[obj] + ",";
                                if (is_list) {
                                    if ( obj == selected_id.length -1 ) {
                                        custom_device_filter_m2m_id += selected_id[obj];
                                    } else {
                                        custom_device_filter_m2m_id += selected_id[obj] + ",";
                                    }
                                } else {
                                    var input_m2m = "<input type='hidden' name='"+m2m_object_name+"' value='"+selected_id[obj]+"'/>";
                                    $("form").append(input_m2m);
                                }
                            }
                            selected_id = []
                                window.custom_device_filter_m2m_id = custom_device_filter_m2m_id;
                                window.return_inspection_devices = selected_id_str;
                                $.fancybox.close();
                                $("#related_devices tr").remove();
                                $.get("/ajax/get-selected-devices?ids=" + selected_id_str, function(data){
                                        $("#related_devices").append("<tr>" +
                                                                              "<td>Id</td>" +
                                                                              "<td>Nr inwentarzowy</td>" +
                                                                              "<td>Nazwa</td>" +
                                                                              "<td>Producent</td>" +
                                                                              "<td>Lokalizacja</td>" +
                                                                           "</tr>");
                                        for (obj in data) {

                                            $("#related_devices").append("<tr>" +
                                                                              "<td><a href='"+data[obj]["url"]+"'>"+obj+".</a></td>" +
                                                                              "<td>"+data[obj]['inventory_number']+"</td>" +
                                                                              "<td>"+data[obj]['name']+"</td>" +
                                                                              "<td>"+data[obj]['make']+"</td>" +
                                                                              "<td>"+data[obj]['location']+"</td>" +
                                                                           "</tr>");
                                        }
                                        $("#related_devices_table_header").show();

                                }, "json");
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "Usuń wszystkie zaznaczenia",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        selected_id = [];
                        $("#filter-devices-table tbody input:checkbox").prop("checked", false);
                        $("#filter-devices-table .check_all").prop("checked", false);
                        oTable.fnDraw();
                    }
                }
            ]
        },
        //"bStateSave": true,
        "bAutoWidth": false,
		"sAjaxSource": '/ajax/filter-devices',
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
		"aoColumns": [
            {
                "mDataProp": "id",
                "fnRender": function ( oObj ) {
                    if (!single_item) {
                        return '<input type=\"checkbox\" id=\"sel'+ oObj.aData["id"] +'\" value="'+ oObj.aData["id"] +'"> ';
                    } else {
                        return '<input name=\"device\" type=\"radio\" id=\"sel'+ oObj.aData["id"] +'\" value="'+ oObj.aData["id"] +'"> ';  
                    }
                },
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
			{ "mDataProp": "status", "bSearchable": true, "sWidth": "6%"} // status
		],
        "fnInitComplete": function(oSettings, json) {

            // columns filter
            $(oSettings.nTable).find("thead").append("<tr></tr>");
            for (c = 0; c<oSettings.aoColumns.length; c++) {
                if (c==0 || c==100) {
                    $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td>&nbsp;</td>");
                } else {
                    $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td><input name=\"search_" + oSettings.aoColumns[c]["mDataProp"] + "\" type=\"text\" value=\"\" /></td>");
                }
            }
            $(oSettings.nTable).find("thead input").keyup(function() {
                oTable.fnFilter( this.value, oTable.oApi._fnVisibleToColumnIndex( oTable.fnSettings(), $("#filter-devices-table thead input").index(this) ) ); // TODO wlasna funkcja do mapowania aktualnej kolumny do wlasciwej (mDataProp) - czy aby na pewno potrzebna?
            });



        },
        "fnDrawCallback": function(){
            refresh_checked_objects();
        }

	});
}

function load_filter_services(m2m_object_name) {
    console.log("#filter-"+m2m_object_name+"s-table");
                $("input[name='"+m2m_object_name+"']").remove();

                $("#filter-"+m2m_object_name+"s-table thead input").keyup( function () {
                    oTableServices.fnFilter( this.value, oTableServices.oApi._fnVisibleToColumnIndex( oTableServices.fnSettings(), $("#filter-"+m2m_object_name+"s-table thead input").index(this) ) );
                } );

                if ( oTableServices !== undefined ) {
                    oTableServices.fnDestroy();
                }
        	    oTableServices = $('#filter-'+m2m_object_name+'s-table').dataTable({
                'sPaginationType': 'full_numbers',
        		"bServerSide": true,
                "bJQueryUI": true,
                'sDom': 'R<"H"TCflr>t<"F"ip>',
                "oColVis": {"sSize": "css",  "buttonText": "Wybór kolumn", "bRestore": true, "sRestore": "<b>Resetuj kolumny</b>"},
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
                "oTableTools": {
                   "sSwfPath": "/site_media/TableTools-2.0.3/media/swf/copy_csv_xls_pdf.swf",
                   "aButtons": [
                        {
                            "sExtends":    "select",
                            "sButtonText": "OK",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                var selected_id_str = "";
                                var custom_service_filter_m2m_id = "";
                                    for (var obj in selected_id) {
                                        selected_id_str += selected_id[obj] + ",";
                                        if (is_list) {
                                            if ( obj == selected_id.length -1 ) {
                                                custom_service_filter_m2m_id += selected_id[obj];
                                            } else {
                                                custom_service_filter_m2m_id += selected_id[obj] + ","
                                            }
                                        } else {
                                            var input_m2m = "<input type='hidden' name='"+m2m_object_name+"' value='"+selected_id[obj]+"'/>";
                                            $("form").append(input_m2m);
                                        }

                                    }
                                    selected_id = []
                                    window.custom_service_filter_m2m_id = custom_service_filter_m2m_id;
                                    $.fancybox.close();
                                    $("#related_services tr").remove();
                                    $.get("/ajax/get-selected-services?ids=" + selected_id_str, function(data){
                                        $("#related_services").append("<tr>" +
                                                                              "<td>Id</td>" +
                                                                              "<td>Opis zgłoszenia</td>" +
                                                                              "<td>Rodzaj</td>" +
                                                                              "<td>Opis</td>" +
                                                                              "<td>Status</td>" +
                                                                              "<td>Osoba zlecająca</td>" +
                                                                              "<td>Firma serwisująca</td>" +
                                                                              "<td>Odbiorca zlecenia</td>" +
                                                                              "<td>Data utworzenia</td>" +
                                                                           "</tr>");
                                        for (obj in data) {
                                            $("#related_services").append("<tr>" +
                                                                              "<td><a href='"+data[obj]["url"]+"'>"+obj+".</a></td>" +
                                                                              "<td>"+data[obj]['description_ticket']+"</td>" +
                                                                              "<td>"+data[obj]['sort']+"</td>" +
                                                                              "<td>"+data[obj]['description']+"</td>" +
                                                                              "<td>"+data[obj]['status']+"</td>" +
                                                                              "<td>"+data[obj]['person_creating']+"</td>" +
                                                                              "<td>"+data[obj]['contractor']+"</td>" +
                                                                              "<td>"+data[obj]['person_completing']+"</td>" +
                                                                              "<td>"+data[obj]['timestamp']+"</td>" +
                                                                           "</tr>");
                                        }
                                        $("#related_services_table_header").show();
                                    }, "json");
                            }
                        },
                        {
                            "sExtends":    "select",
                            "sButtonText": "Usuń wszystkie zaznaczenia",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                selected_id = [];
                                $("table tbody input:checkbox").prop("checked", false);
                                $("#filter-"+m2m_object_name+"s-table .check_all").prop("checked", false);
                                oTable.fnDraw();
                            }
                        }
                    ]
                },
                //"bStateSave": true,
                "bAutoWidth": false,
        		"sAjaxSource": '/ajax/filter-services',
        		"aoColumns": [
                        {
                            "mDataProp": "id",
                            "fnRender": function ( oObj ) {
                                return '<input type=\"checkbox\" id=\"sel'+ oObj.aData["id"] +'\" value="'+ oObj.aData["id"] +'"> ';
                            },
                            "aTargets": [ 0 ],
                            "bSortable": false, "sWidth": "1%"
                        },
        			    { "mDataProp": "lp", "bSearchable": true, "sWidth": "10%"},
        			    { "mDataProp": "ticket", "bSearchable": true, "sWidth": "20%"},
        			    { "mDataProp": "sort", "bSearchable": true, "bSortable": true},
        			    { "mDataProp": "person_assigned", "bSearchable": true},
        			    { "mDataProp": "description", "bSearchable": true},
        			    { "mDataProp": "status", "bSearchable": true},
        			    { "mDataProp": "person_creating", "bSearchable": true},
        			    { "mDataProp": "contractor", "bSearchable": true},
        			    { "mDataProp": "person_completing", "bSearchable": true},
        			    { "mDataProp": "timestamp", "bSearchable": true}
        		    ],

                "fnInitComplete": function(oSettings, json) {
                    // columns filter
                    $(oSettings.nTable).find("thead").append("<tr></tr>");
                    for (c = 0; c<oSettings.aoColumns.length; c++) {
                        if (c==0 || c==100) {
                            $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td>&nbsp;</td>");
                        } else {
                            $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td><input name=\"search_" + oSettings.aoColumns[c]["mDataProp"] + "\" type=\"text\" value=\"\" /></td>");
                        }
                    }
                    $(oSettings.nTable).find("thead input").keyup(function() {
                        oTableServices.fnFilter( this.value, oTableServices.oApi._fnVisibleToColumnIndex( oTableServices.fnSettings(), $("#filter-"+m2m_object_name+"s-table thead input").index(this) ) ); // TODO wlasna funkcja do mapowania aktualnej kolumny do wlasciwej (mDataProp) - czy aby na pewno potrzebna?
                    });
                },
                "fnDrawCallback":function(){
                    refresh_checked_objects();
                }
        });
}

function load_filter_tickets(m2m_object_name) {
            $("input[name='ticket']").remove();
            if ( oTableTickets !== undefined ) {
                oTableTickets.fnDestroy();
            }
            $("#filter-tickets-table thead input").keyup( function () {
                oTableTickets.fnFilter( this.value, oTableTickets.oApi._fnVisibleToColumnIndex( oTableTickets.fnSettings(), $("#filter-tickets-table thead input").index(this) ) );
            } );
            oTableTickets = $('#filter-tickets-table').dataTable({
            'sPaginationType': 'full_numbers',
            "bServerSide": true,
            "bJQueryUI": true,
            'sDom': 'R<"H"TCflr>t<"F"ip>',
            "oColVis": {"sSize": "css",  "buttonText": "Wybór kolumn", "bRestore": true, "sRestore": "<b>Resetuj kolumny</b>"},
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
            "oTableTools": {
            "sSwfPath": "/site_media/TableTools-2.0.3/media/swf/copy_csv_xls_pdf.swf",
            "aButtons": [
                {
                    "sExtends":    "select",
                    "sButtonText": "OK",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        var selected_id_str = "";
                        var custom_ticket_filter_m2m_id = "";
                            for (var obj in selected_id) {
                                selected_id_str += selected_id[obj] + ",";
                                if (is_list) {
                                    if ( obj == selected_id.length -1 ) {
                                        custom_ticket_filter_m2m_id += selected_id[obj];
                                    } else {
                                        custom_ticket_filter_m2m_id += selected_id[obj] + ","
                                    }

                                } else {
                                    var input_m2m = "<input type='hidden' name='"+m2m_object_name+"' value='"+selected_id[obj]+"'/>";
                                    $("form").append(input_m2m);
                                }
                            }

                            selected_id = [];
                            window.custom_ticket_filter_m2m_id = custom_ticket_filter_m2m_id;
                            $.fancybox.close();
                            $("#related_tickets tr").remove();
                            $.get("/ajax/get-selected-tickets?ids=" + selected_id_str, function(data){
                                $("#related_tickets").append("<tr>" +
                                                                      "<td>Id</td>" +
                                                                      "<td>Data</td>" +
                                                                      "<td>Rodzaj</td>" +
                                                                      "<td>Opis</td>" +
                                                                      "<td>Osoba zgłaszająca</td>" +
                                                                      "<td>Status</td>" +
                                                                      "<td>Osoba zamykająca</td>" +
                                                                      "<td>Data zamknięcia</td>" +
                                                                   "</tr>");
                                for (obj in data) {
                                    $("#related_tickets").append("<tr>" +
                                                                      "<td><a href='"+data[obj]["url"]+"'>"+obj+".</a></td>" +
                                                                      "<td>"+data[obj]['timestamp']+"</td>" +
                                                                      "<td>"+data[obj]['sort']+"</td>" +
                                                                      "<td>"+data[obj]['description']+"</td>" +
                                                                      "<td>"+data[obj]['person_creating']+"</td>" +
                                                                      "<td>"+data[obj]['status']+"</td>" +
                                                                      "<td>"+data[obj]['person_closing']+"</td>" +
                                                                      "<td>"+data[obj]['date_closing']+"</td>" +
                                                                   "</tr>");
                                }
                                $("#related_tickets_table_header").show();



                            }, "json");
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "Usuń wszystkie zaznaczenia",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        selected_id = [];
                        $("#filter-tickets-table tbody input:checkbox").prop("checked", false);
                        $("#filter-tickets-table .check_all").prop("checked", false);
                        oTable.fnDraw();
                    }
                }
            ]
        },
            //"bStateSave": true,
            "bAutoWidth": false,
            "sAjaxSource": '/ajax/filter-tickets',
            "aoColumns": [
                    {
                        "mDataProp": "id",
                        "fnRender": function ( oObj ) {
                            return '<input type=\"checkbox\" id=\"sel'+ oObj.aData["id"] +'\" value="'+ oObj.aData["id"] +'"> ';
                        },
                        "aTargets": [ 0 ],
                        "bSortable": false, "sWidth": "1%"
                    },
                    { "mDataProp": "lp", "bSearchable": true, "sWidth": "10%"},
                    { "mDataProp": "timestamp", "bSearchable": true, "sWidth": "20%"},
                    { "mDataProp": "sort", "bSearchable": true, "bSortable": true},
                    { "mDataProp": "description", "bSearchable": true},
                    { "mDataProp": "person_creating", "bSearchable": true},
                    { "mDataProp": "status", "bSearchable": true},
                    { "mDataProp": "person_closing", "bSearchable": true},
                    { "mDataProp": "date_closing", "bSearchable": true}
                ],
            "fnInitComplete": function(oSettings, json) {
                // columns filter
                $(oSettings.nTable).find("thead").append("<tr></tr>");
                for (c = 0; c<oSettings.aoColumns.length; c++) {
                    if (c==0 || c==100) {
                        $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td>&nbsp;</td>");
                    } else {
                        $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td><input name=\"search_" + oSettings.aoColumns[c]["mDataProp"] + "\" type=\"text\" value=\"\" /></td>");
                    }
                }
                $(oSettings.nTable).find("thead input").keyup(function() {
                    oTableTickets.fnFilter( this.value, oTableTickets.oApi._fnVisibleToColumnIndex( oTableTickets.fnSettings(), $("#filter-tickets-table thead input").index(this) ) ); // TODO wlasna funkcja do mapowania aktualnej kolumny do wlasciwej (mDataProp) - czy aby na pewno potrzebna?
                });
            },
            "fnDrawCallback":function(){
                refresh_checked_objects();
            }
        });
}
