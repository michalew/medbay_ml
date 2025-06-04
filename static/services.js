$(document).ready(function() {
    // check all, uncheck all
    $("#services-table thead #s_selall").click(function() {
            $("#services-table tbody input:checkbox").prop("checked", $(this).prop("checked"));
    });

    $('#services-table tbody').on("click", "tr td input", function(event) {
        // manage selected service for current device (Device.selected_services)
        var service_id = $(this).val();
        if ($(this).prop("checked")) {
            Device.selected_services.push(service_id);
        } else {
            var arr_index = $.inArray(service_id, Device.selected_services);
            if (arr_index>-1) Device.selected_services.splice(arr_index, 1);
        }
        // service table multiple rows selected
        //$(this).toggleClass('row_selected');
    });

    $("#services-table tbody").click(function(event) {
        var checkbox_clicked = event.target.id.match(/s_sel\d+/); // sprwdzamy czy kliknieto w checkbox, jesli nie to Device.checkbox_clicked == null ...
        if (checkbox_clicked == null) { // kliknieto w row (nie w checkbox) wiec zaznaczamy row (row_selected)
            $("#services-table tr.row_selected").removeClass('row_selected');
            $(event.target.parentNode).addClass('row_selected');
        }
    });
});

function add_service(arr, edit) { // funckja udpalana jako callback dla przycisku "dodaj zlecenie"

    var form; var form_url;
    if (edit) {
        form_url = "/nowe-zlecenie?id=" + arr; // arr == service_id
        //if (!(Device.selected_services[0])) form_url = "/nowe-zlecenie?id=" + arr[0];
    } else { 
        form_url = "/nowe-zlecenie?tickets=" + arr.join();
    }

    $.get(form_url, function(data) {
    
        $.fancybox(
                data,
                {
                    'onClosed': function() { // service selection handling when updating service thru services table
                        if (oTableServices && Device.saved_service) { 
                            Device.saved_service = false; 
                            var ss_arr = Device.selected_services;
                            for (var t in ss_arr) {
                                $("#services-table tr td:first-child:contains('" + ss_arr[t] + "')").parent().addClass('row_selected');
                            }
                        }
                    }
                }
        );

        if ($("#id_sort").val()==0) $("#id_contractor").parent().parent().hide();
        if ($("#id_sort").val()==1) $("#id_person_completing").parent().parent().hide();
        $("#id_sort").on("change", function(e) {
            if ($(this).val() == 0) {
                $("#id_contractor").parent().parent().hide(); 
                $("#id_person_completing").parent().parent().show();
            } else {
                $("#id_person_completing").parent().parent().hide();
                $("#id_contractor").parent().parent().show(); 
            }
        });
    

        $("#add-service").on("submit", function() {
    
            $.fancybox.showActivity();
    
            save_service(arr, User, edit)
            
            return false;
    
        }); // .on

    }); // .get

}

function open_service_preview(service_id) {
    
    var form_url = "/podglad-zlecenia/" + service_id;

    $.get(form_url, function(data) {
        $.fancybox(data);
    }).done( function() {
        $(".print").on("click", function() { 
            $(".action-form").printElement();
        });
        $(".print-service").on("click", function() {
            generate_pdf_directly("service", service_id);
        });
    }); // .get
}
function save_service(arr, User, edit) {
    var ticket_arr = Array();
    for (var i in arr) {
        ticket_arr.push("/api/v1/ticket/" + arr[i] + "/");   
    }

    var data = {
            "ticket": ticket_arr,
            "sort": parseInt($("#id_sort").val()),
            "person_assigned": "/api/v1/userprofile/" + $("#id_person_assigned").val() + "/",
            "description": $("#id_description").val(),
            "status": $("#id_status").val(),
            "person_creating": "/api/v1/userprofile/" + User.id + "/",
            "contractor": "/api/v1/contractor/" + $("#id_contractor").val() + "/", //TODO: czy firma serwisujaca ma byc brana z urzadzenia?
            "person_completing": "/api/v1/userprofile/" + $("#id_person_completing").val() + "/",
            "hospital": "/api/v1/hospital/" + $("#id_hospital").val() + "/",
        };
    if ($("#id_person_assigned").val() == "") delete data.person_assigned; // usuwamy jesli nie wybrano osoby przypisanej bo inaczej dodawanie jej daje 404
    if ($("#id_contractor").val() == "") delete data.contractor; 
    if ($("#id_person_completing").val() == "") delete data.person_completing; 
    if ($("#id_hospital").val() == "") delete data.hospital; 
    //if (edit) delete data.ticket; // nie aktualizujemy zgloszenia wiec usuwamy je z data

    // add or edit ...
    var request_type = "POST";
    if (edit) request_type = "PUT";
    var request_url = "/api/v1/service/";
    if (edit) request_url = "/api/v1/service/" + Device.selected_services[0] + "/";
    var msg_success = "Wysłano zlecenie dla wybranych zgłoszeń.";
    if (edit) msg_success = "Zaktualizowano zlecenie";

    $.ajax({
	    type: request_type,
        contentType: "application/json",
	    cache: false,
	    url: request_url,
	    data: JSON.stringify(data),
	    success: function(response) {
            $(".action-form h1").html(msg_success);
            if (!edit) $("#service-preview").fadeIn();
            //$("#add-service input, #add-ticket select, #add-ticket textarea").not("#add-service #submit-row input:first-child").prop("disabled", true);
            $("#add-service #submit-row input:first-child").prop("disabled", true); //.val("Zapisz").on("click", function() { save_service([response.id], User, edit=true); }) ; //TODO save, not add!
            $("#service-preview").on("click", function() { open_service_preview(response.id) });
            Device.saved_service = true;
            if (oTableServices) oTableServices.fnDraw(false);
            $.fancybox.hideActivity();
	    }
	});

}

function load_services() { // funkcja odpalana gdy wybierzemy urzadzenie - buduje tabelke ze zleceniami tego urzadzenia

                if (oTableServices!==undefined) {
                    //oTableTickets.fnClearTable();
                    oTableServices.fnDestroy();
                }
        	    oTableServices = $('#services-table').dataTable({
                'sPaginationType': 'full_numbers', 
        		"bServerSide": true, 
                //"bRetrieve": true,
                //"bDestroy": true,
                "bJQueryUI": true,
                'sDom': 'R<"H"<"arrow">TCfr>t<"F"ilp>',
                "oColVis": {"aiExclude": [ 0 ], "sSize": "css",  "buttonText": "<i class='icon icon-columns'></i> Wybór kolumn", "bRestore": true, "sRestore": "<b>Resetuj kolumny</b>"},
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
                            "sButtonText": "<i class='fa fa-file-excel-o'></i> Eksportuj do XLS",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                tmp_arr = [];
                                $("#services-table tbody input:checked").each(function(index) { tmp = $(this).val(); tmp_arr.push(tmp); });
                                if (tmp_arr.length > 0) { generate_xls('Service', tmp_arr); } else { alert("Proszę wybrać przynajmniej jedno zgłoszenie"); return false; }
                            }
                        },
                        {
                            "sExtends":    "select",
                            "sButtonText": "<i class='fa fa-eye'></i> Podgląd zlecenia",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                tmp_arr = []; // zbieramy zaznaczone (row_selected) zgloszenia dla funkcji add_service
                                var service_id = $("#services-table tbody tr.row_selected td:first-child input").val();
                                if (service_id) {
                                    open_service_preview(service_id)
                                } else { 
                                    alert("Proszę wybrać jedno zlecenie"); return false;
                                }
                            }
                        },
                        {
                            "sExtends":    "select",
                            "sButtonText": "<i class='fa fa-pencil'></i> Edycja zlecenia",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                tmp_arr = []; // zbieramy zaznaczone (row_selected) zgloszenia dla funkcji add_service
                                var service_id = $("#services-table tbody tr.row_selected td:first-child input").val();
                                if (service_id) {
                                    window.open("/a/cmms/service/" + service_id + "/");
                                } else { 
                                    alert("Proszę wybrać jedno zlecenie"); return false;
                                }
                            }
                        },
                        {
                            "sExtends":    "select",
                            "sButtonText": "<i class='fa fa-file-pdf-o'></i> Utwórz PDF",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                var service_id = $("#services-table tbody tr.row_selected td:first-child input").val();
                                if (service_id) {
                                    generate_pdf("Service", service_id);
                                } else { 
                                    alert("Proszę wybrać jedno zlecenie"); return false;
                                }
                            }
                        }
                    ]
                },
                "bStateSave": true,
                "fnStateSave": function (oSettings, oData) {
                    localStorage.setItem( 'DataTables_services', JSON.stringify(oData) );
                },
                "fnStateLoad": function (oSettings) {
                    return JSON.parse( localStorage.getItem('DataTables_services') );
                },
                "bAutoWidth": false,
        		"sAjaxSource": Urls.services + "/" + Device.id,
        		"aoColumns": [
                        { "mDataProp": "id", 
                            "fnRender": function ( oObj ) {
                                return '<input type=\"checkbox\" id=\"s_sel' + oObj.aData["id"] + '\" value="' + oObj.aData["id"] + '">';
                                //return o.aData[0] +' '+ o.aData[3];
                            },
                          "aTargets": [ 0 ],
                          "bSortable": false, "sWidth": "1%"
                        },
        			    { "mDataProp": "lp", "bSearchable": true, "sWidth": "10%"},
        			    { "mDataProp": "ticket", "bSearchable": true, "sWidth": "20%"},
        			    { "mDataProp": "sort", "bSearchable": false, "bSortable": true},
        			    { "mDataProp": "person_assigned", "bSearchable": true},
        			    { "mDataProp": "description", "bSearchable": false},
        			    { "mDataProp": "status", "bSearchable": false},
        			    { "mDataProp": "person_creating", "bSearchable": false},
        			    { "mDataProp": "contractor", "bSearchable": false},
        			    { "mDataProp": "person_completing", "bSearchable": false},
        			    { "mDataProp": "timestamp", "bSearchable": false}
        		    ]
        	    });

}
