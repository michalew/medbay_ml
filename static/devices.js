$.fn.wait = function(time, type) {
        time = time || 1000;
        type = type || "fx";
        return this.queue(type, function() {
            var self = this;
            setTimeout(function() {
                $(self).dequeue();
            }, time);
        });
    };
$(document).ready(function() {

    // check all, uncheck all
    $("#devices-table thead #selall").click(function() {
        var _checked = $(this).prop("checked");
        $("#devices-table tbody input:checkbox").prop("checked", _checked).each(function() {
            var _id = $(this).attr("id");
            var device_id = _id.replace("sel", "");

            var _sd = localStorage.selected_devices;
            if (_sd) _sd = JSON.parse(_sd)
            else _sd = new Object()

            if (_checked && !_sd[device_id]) _sd[device_id]= _id;
            else delete(_sd[device_id]);

            localStorage.selected_devices = JSON.stringify(_sd);

        });
    });

    /*
     * tabelka górna (z urządzeniami) - obsługa kliknięć. Po kliknięciu w row z urządzeniem
     * pojawia się dolna tabelka i ładuję się do niej odpowiednie dane.
     * jeśli zaznaczono checkbox wykonuje się update tablicy, w której przetrzymywane są zaznaczone urządzenia (wykorzystywane w innych miejscach)
     * oraz obsługiwane jest zachowanie checkboxa w headerze kolumny: jeśli ktoś ręcznie wybierze wszystkie checkboxy to powinien się zaznaczyć automatycznie - i odwrotnie.
     */
    $("#devices-table tbody").click(function(event) {
        Device.checkbox_clicked = event.target.id.match(/sel(\d+)/); // sprwdzamy czy kliknieto w checkbox, jesli nie to Device.checkbox_clicked == null ...
        if (Device.checkbox_clicked == null) { // kliknieto w row (nie w checkbox) wiec zaznaczamy row (row_selected)
            $("#bottom-part").show();
            $("#devices-table tr.row_selected").removeClass('row_selected');
            $(event.target.parentNode).addClass('row_selected');
            Device.id = event.target.parentNode.firstChild.firstChild.value; // tr td input

            var currentTab = $("ul.device-tabs li a.active").attr("href").replace("#", "");
            if (currentTab == 'zgloszenia') load_tickets(); // tabelka ze zgloszeniami
            if (currentTab == 'zlecenia') load_services(); // budujemy tabelke ze zleceniami dla wybranego urzadzenia
            if (currentTab == 'serwis') load_service_history();
            if (currentTab == 'dokumenty') load_device_documents();
            if (currentTab == 'licznik') load_mileage();
            if (currentTab == 'galeria') load_device_gallery();
            /*
            load_device_instructions(); #TODO - co to?
            */
        } else { // Device.checkbox_clicked is a \d+
            // add/remove clicked device into array/object (cookie/local storage): add if checked and not present yet, remove when unchecked and already present
            var _device_id = Device.checkbox_clicked[1];
            var _id = Device.checkbox_clicked[0];
            var _sd = localStorage.selected_devices;
            if (_sd) _sd = JSON.parse(_sd)
            else _sd = new Object()

            if (_sd[_device_id]) {
                delete(_sd[_device_id]);
            } else {
                _sd[_device_id]= _id;
            }

                //update_counter("decrease");
            localStorage.selected_devices = JSON.stringify(_sd);

            handle_checkall();

        }
    });
});

function print_devices_table(){
    var ids = [];
    $("#devices-table tbody input:checked").each(function() {
        var id = $(this).val();
        ids.push(id);
    });

    if (ids.length > 0) {
        generate_pdf_directly("all_table", ids);
    } else {
        alert("Proszę wybrać conajmniej jedno urządzenie"); return false;
    }
}

function print_devices_qrcodes(){
    var ids = [];
    $("#devices-table tbody input:checked").each(function() {
        var id = $(this).val();
        ids.push(id);
    });

    if (ids.length > 0) {
        form_url = "/qrcode-generate/?ids=" + ids
        location.href = form_url;
    } else {
        alert("Proszę wybrać conajmniej jedno urządzenie"); return false;
    }
}

function print_passport(){
    var ids = []
    $("#devices-table tbody input:checked").each(function(index) { var id = $(this).val(); ids.push(id); });

    if (ids.length > 0) {
        generate_pdf_directly("passport", ids);
    } else {
        alert("Proszę wybrać conajmniej jedno urządzenie"); return false;
    }
}

function clear_columns_filter(oTable){
    $("[name^='search']").val("")
    var oSettings = oTable.fnSettings();
    for(iCol = 0; iCol < oSettings.aoPreSearchCols.length; iCol++) {
      oSettings.aoPreSearchCols[ iCol ].sSearch = '';
    }
    oTable.fnDraw();
}

function preview_device() { // funckja udpalana jako callback dla przycisku "podgląd urządzenia"

    // jeśli edycja podgląd (edycja) urządzenia to ładujemy formularz wypełniony danymi urządzenia
    var form; var form_url;
    form_url = "/podglad-urzadzenia?id=" + Device.id;

    $.get(form_url, function(data) { // pobieramy ajaxem formularz
        $.fancybox( // żeby ładnie było
            data,
            {
                'onClosed': function() {
                    if (Device.saved) {
                        oTable.$("#sel" + Device.id).parent().parent().addClass('row_selected'); // zaznaczamy row spowrotem
                        Device.saved = false;
                    }
                },
                'onCleanup': function() {
                    //oTable.fnDraw(false);
                }
            }
        );

    }).done( function() {
        $(".print").on("click", function() { 
            $(".action-form").printElement();
        });
        $(".print-device").on("click", function() {
            generate_pdf_directly("device", Device.id);
        });
    });
}

function load_devices() { // funkcja buduje tabelke z urzadzeniami
    oTable = $('#devices-table').dataTable({ // init the devices table
		'sPaginationType': 'full_numbers', 
		"bServerSide": true, 
        "bJQueryUI": true,
        'sDom': '<"H"<"arrow">TRCfr>t<"F"ilp>', // odsyłam do dokumentacji datatables :) jest całkiem niezła: http://datatables.net/reference/option/dom
        "oTableTools": {
            "sSwfPath": "/site_media/DataTables-1.9.1/extras/TableTools/media/swf/copy_csv_xls_pdf.swf",
            "aButtons": [
                {
                    "sExtends":    "select",
                    "sButtonText": "<i class='fa fa-plus-circle'></i> Dodaj zgłoszenie",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        tmp_arr = [];
                        $("#devices-table tbody input:checked").each(function(index) { tmp = $(this).val(); tmp_arr.push(tmp); });
                        if (tmp_arr.length > 0) { add_ticket(tmp_arr); } else { alert("Proszę wybrać przynajmniej jedno urządzenie"); return false; }
                    }
                }, {
                    "sExtends": "collection",
                    "sButtonText": "<i class='fa fa-print'></i> Drukuj",
                    "aButtons": [
                        {
                            "sExtends":    "select",
                            "sButtonText": "<i class='fa fa-file-excel-o'></i> Eksportuj do XLS",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                device_ids = [];
                                $("#devices-table tbody input:checked").each(function(index) { var id = $(this).val(); device_ids.push(id); });
                                if (device_ids.length > 0) { generate_xls('Device', device_ids); } else { alert("Proszę wybrać przynajmniej jedno urządzenie"); return false; }
                            }
                        }, {
                            "sExtends":    "select",
                            "sButtonText": "<i class='fa fa-print'></i> Drukuj paszport",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                print_passport();
                            }
                        }, {
                            "sExtends":    "select",
                            "sButtonText": "<i class='fa fa-file-pdf-o'></i> Drukuj PDF",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                print_devices_table();
                            }
                        }, {
                            "sExtends":    "select",
                            "sButtonText": "<i class='fa fa-qrcode'></i> Drukuj kody QR",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                print_devices_qrcodes();
                            }
                        },
                    ],
                }, {
                    "sExtends":    "select",
                    "sButtonText": "<i class='fa fa-eye'></i> Podgląd urządzenia",
                    "fnClick": function ( nButton, oConfig, oFlash ) {                        
                        if (!Device.id) { alert("Proszę zazanaczyć urządzenie"); return false; }
                        preview_device()
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "<i class='fa fa-pencil'></i> Edycja urządzenia",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        if (!Device.id) { alert("Proszę zazanaczyć urządzenie"); return false; }
                        window.open("/a/cmms/device/"+Device.id)
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "<i class='fa fa-plus-circle'></i> Dodaj urządzenie",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        window.open("/a/cmms/device/add")
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "<i class='fa fa-filter'></i> Czyść filtry",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        //clear_columns_filter(oTable);
                        fnLocalStorageReset();
                        location.reload();
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
		"sAjaxSource": Urls.devices, // url do źródła danych dla tabeli: /ajax/devices - serwuje jsona z urządzeniami; w urls.py to jest url ajax_devices
		"oColVis": {"aiExclude": [ 0 ], "sSize": "css", "buttonText": "<i class='icon icon-columns'></i> Wybór kolumn", "bRestore": true, "sRestore": "<b>Resetuj kolumny</b>", "fnStateChange": function ( iColumn, bVisible ) {
            $("#devices-table thead tr:last-child td:nth-child(" + (iColumn + 1) + ")").toggleClass("hidden", !bVisible);
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
        "aaSorting": [[ 8, "asc" ], [ 2, "asc" ]], // sort by location, name
		"aoColumns": [
            {
                "mDataProp": "id", 
                "fnRender": function ( oObj ) {
                    var checked_str = "";
                    var _sd = localStorage.selected_devices;
                    if (_sd) {
                        _sd = JSON.parse(_sd);
                        if (_sd.hasOwnProperty(oObj.aData.id)) checked_str = " checked=\"checked\" ";
                    }

                    return '<input type=\"checkbox\"' + checked_str + 'id=\"sel'+ oObj.aData["id"] +'\" value="'+ oObj.aData["id"] +'"> ';
                },
                "aTargets": [ 0 ],
                "bSortable": false, "sWidth": "1%",
            },
			{ "mDataProp": "lp", "bSearchable": true, "sWidth": "1%"}, // lp
			{ "mDataProp": "name", "bSearchable": true, "sWidth": "15%"}, // nazwa
			{ "mDataProp": "genre", "bSearchable": true, "sWidth": "8%", "bVisible": false}, // rodzaj
			{ "mDataProp": "model", "bSearchable": true, "sWidth": "8%"}, // model
			{ "mDataProp": "make", "bSearchable": true, "sWidth": "8%"}, // producent
			{ "mDataProp": "serial_number", "bSearchable": true, "sWidth": "10%"}, // nr seryjny
			{ "mDataProp": "inventory_number", "bSearchable": true, "sWidth": "10%"}, // nr inwentarzowy
			{ "mDataProp": "location", "bSearchable": true, "sWidth": "8%"}, // lokalizacja
            { "mDataProp": "location_place", "bSearchable": true, "sWidth": "8%"}, // lokalizacja miejsce
			{ "mDataProp": "person_responsible", "bSearchable": true, "sWidth": "8%", "bVisible": false}, // osoba odpowiedzialna
			{ "mDataProp": "technical_supervisor", "bSearchable": true, "sWidth": "8%", "bVisible": false}, // nadzor techniczny
            { "mDataProp": "date_service", "bSearchable": true, "sWidth": "6%" }, // data przeglądu
            { "mDataProp": "date_next_service", "bSearchable": true, "sWidth": "6%" }, // data następnego przeglądu
            { "mDataProp": "status", "bSearchable": true, "sWidth": "6%", "sClass": "status"}, // status
            { "mDataProp": "date_warranty", "bSearchable": true, "sWidth": "6%", "bVisible": false} // date_warranty
		],
        "fnInitComplete": function(oSettings, json) { // różne rzeczy po inicjacji tabeli (on DOM ready)
            if (blink) { // obsolete
                $("#ToolTables_devices-table_0").css({'font-weight': 'bold'});
                $(oSettings.nTable).find("td:first-child").each(function () {
                    checkbox = $(this).find("input");
                });
                blink = false;
            }
            if (new_device) { // jeśli przywędrowaliśmy skądinąd aby dodać urządzenie boldujemy przycisk do tego służący
                $("#ToolTables_devices-table_1").css({'font-weight': 'bold'});
                new_device = false;
                add_device();
            }
            if (device_id) { // jeśli przywędrowaliśmy skądinąd aby obejrzeć bezpośrednio jakieś urządzenie to zaznaczamy je od razu, żeby dolna część też się załadowała automatycznie
                $("#devices-table tbody tr td:nth-child(2)").trigger("click");
            }
            $(".print-table").text("Drukuj listę");
            $(".print-table").on("click", function() {
                $("#devices-table").printElement();
            });

            $(oSettings.nTable).find("thead").append("<tr></tr>");
            for (c = 0; c<oSettings.aoColumns.length; c++) {
                if (c==0 || c==100) { // placeholder dla info o liczbie zaznaczonych urządzeń - WIP na innym branchu
                    $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td id=\"device-selection-info\">&nbsp;</td>");
                } else {
                    var _class = (oSettings.aoColumns[c].bVisible) ? "" : " class=\"hidden\"";
                    $(oSettings.nTable).find("thead tr:nth-child(2)").append("<td" + _class + "><input name=\"search_" + oSettings.aoColumns[c]["mDataProp"] + "\" type=\"text\" value=\"" + oSettings.aoPreSearchCols[c].sSearch + "\" /></td>");
                }
            }

            $(oSettings.nTable).find("thead input").keyup(function() {
                let column_index = $("#devices-table thead td:not(.hidden) input").index(this) + 1;
                let datatables_column_index = oTable.oApi._fnVisibleToColumnIndex(oTable.fnSettings(), column_index);
                oTable.fnFilter(this.value, datatables_column_index); // TODO wlasna funkcja do mapowania aktualnej kolumny do wlasciwej (mDataProp) - czy aby na pewno potrzebna?
            });
        },
        "fnDrawCallback": handle_checkall,
        "fnRowCallback": function( nRow, aData, iDisplayIndex, iDisplayIndexFull ) {
            if ( aData.status == "Uszkodzone" ) $(nRow).addClass("uszkodzone")
            if ( aData.has_service == "True" ) $(nRow).addClass("umowa-serwisowa")
            if ( Date.parse(aData.date_warranty) > Date.now() ) $(nRow).addClass("na-gwarancji")
        }
	});

    // permissions stuff
    if (window.user_group_permissions.indexOf("cmms.add_device") < 0)
        $('#ToolTables_devices-table_6').css("display","none");
    
    if (window.user_group_permissions.indexOf("cmms.view_device") < 0)
        $('#ToolTables_devices-table_4').css("display","none");
    
    if (window.user_group_permissions.indexOf("cmms.change_device") < 0)
        $('#ToolTables_devices-table_5').css("display","none");
    
    if (window.user_group_permissions.indexOf("cmms.add_ticket") < 0)
        $('#ToolTables_devices-table_0').css("display","none");
}

function handle_checkall() {
    var checked_count = $("#devices-table tbody input:checked").length;
    var rows_count = $("#devices-table tbody tr").length;
    if ( checked_count < rows_count ) $("#devices-table thead #selall").prop("checked", false);
    if ( checked_count == rows_count ) $("#devices-table thead #selall").prop("checked", true);
}

/*
 * obsługa info o liczbie zaznaczonych urządzeń
 * przechowywane w localstorage bo cookies ma ograniczoną pojemność (4KB)
 */
function update_counter(action) {
    var _sd = localStorage.selected_devices;
    if (_sd) _sd = JSON.parse(_sd)
    else _sd = new Object()
    
    var cnt = 0;

    for (d in _sd) { if (_sd.hasOwnProperty(d)) cnt++ }

    $("#device-selection-info").html(cnt);
}
