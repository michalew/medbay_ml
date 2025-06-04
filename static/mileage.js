$(document).ready(function() {
    // check all, uncheck all
    $("#mileage-table thead #m_selall").click(function() {
            $("#mileage-table tbody input:checkbox").prop("checked", $(this).prop("checked"));
    });

    $('#mileage-table tbody').on("click", "tr td input", function(event) {
        // manage selected mileage for current device (Device.selected_services)
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

    $("#mileage-table tbody").click(function(event) {
        var checkbox_clicked = event.target.id.match(/m_sel\d+/); // sprwdzamy czy kliknieto w checkbox, jesli nie to Device.checkbox_clicked == null ...
        if (checkbox_clicked == null) { // kliknieto w row (nie w checkbox) wiec zaznaczamy row (row_selected)
            $("#mileage-table tr.row_selected").removeClass('row_selected');
            $(event.target.parentNode).addClass('row_selected');
        }
    });

    $("#xmileage-preview").click(function() { // TODO?
        $.get("/podglad-licznika/" + Device.selected_services[0], function(data) {
            $.fancybox(
                    data,
                    {
                        'onClosed': function() {
                            // sdfsdf
                        }
                    }
            );
        });
    });
});

function add_mileage(arr, edit) { // funckja odpalana jako callback dla przycisku "dodaj licznik"

    var form; var form_url;
    if (edit) {
        form_url = "/nowy-licznik?id=" + arr // arr == mileage_id
    } else { 
        form_url = "/nowy-licznik?device_id=" + arr // arr == device_id
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
                                $("#mileage-table tr td:first-child:contains('" + ss_arr[t] + "')").parent().addClass('row_selected');
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
    

        $("#add-mileage").on("submit", function() {
    
            $.fancybox.showActivity();
    
            save_mileage(arr, User, edit)
            
            return false;
    
        }); // .on

    }).done(function() {
        if (edit) $("#mileage-preview").show().prop("disabled", false);
    }); // .get
}

function open_mileage_history(mileage_id) {
    $.get("/podglad-licznika/" + mileage_id, function(data) {
        $.fancybox(data);
    }).done(); // .get
}

function save_mileage(arr, User, edit) {
    var data = {
            "remarks": $("#id_remarks").val(),
            "state": $("#id_state").val(),
            "status": $("#id_status").val(),
            "device": $("#id_device").val()
        };

    // add or edit ...
    var request_type = "POST";
    if (edit) request_type = "PUT";
    var request_url = "/api/v1/mileage/";
    if (edit) request_url = "/api/v1/mileage/" + arr + "/";
    var msg_success = "Nowy licznik yay yay yay";
    if (edit) msg_success = "Zaktualizowano licznik";

    $.ajax({
	    type: request_type,
        contentType: "application/json",
	    cache: false,
	    url: request_url,
	    data: JSON.stringify(data),
	    success: function(response) {
            $(".action-form h1").html(msg_success);
            if (!edit) $("#mileage-preview").fadeIn();
            $("#add-mileage #submit-row input:first-child").prop("disabled", true);
            $("#mileage-preview").on("click", function() { open_mileage_history(response.id) });
            Device.saved_mileage = true;
            if (oTableMileage) oTableMileage.fnDraw(false);
            $.fancybox.hideActivity();
	    },
        error: function(jqXHR, textStatus, errorThrown){
            var error = jQuery.parseJSON(jqXHR.responseText);
            alert(error.error_message);
            $.fancybox.hideActivity();
        }
	});
}

function reset_mileage(arr) {
    var data = {
            "reset": true,
        };

    // add or edit ...
    var request_type = "PUT";
    var request_url = "/api/v1/mileage/" + arr + "/";
    var msg_success = "Zresetowano licznik";

    $.ajax({
	    type: request_type,
        contentType: "application/json",
	    cache: false,
	    url: request_url,
	    data: JSON.stringify(data),
	    success: function(response) {
            $(".action-form h1").html(msg_success);
            Device.saved_mileage = true;
            if (oTableMileage) oTableMileage.fnDraw(false);
            $.fancybox.hideActivity();
	    },
        error: function(jqXHR, textStatus, errorThrown){
            var error = jQuery.parseJSON(jqXHR.responseText);
            alert(error.error_message);
            $.fancybox.hideActivity();
        }
	});
}


function load_mileage() { // funkcja odpalana gdy wybierzemy urzadzenie - buduje tabelke z licznikami tego urzadzenia
                if (oTableMileage!==undefined) {
                    oTableMileage.fnDestroy();
                }
        	    oTableMileage = $('#mileage-table').dataTable({
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
                            "sButtonText": "<i class='fa fa-pencil'></i> Wprowadź licznik",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                // check if user has permissions
                                if (window.user_group_permissions.indexOf("cmms.update_mileage") < 0) {
                                    alert("Brak wymaganych uprawnień!");
                                    return false;
                                }
                                
                                tmp_arr = []; // zbieramy zaznaczone (row_selected) zgloszenia dla funkcji add_ticket
                                var mileage_id = $("#mileage-table tbody tr.row_selected td:first-child input").val();
                                if (mileage_id) {
                                    add_mileage(mileage_id,edit=true);
                                } else { 
                                    alert("Proszę wybrać jeden licznik"); return false;
                                }
                            }
                        },
                        {
                            "sExtends":    "select",
                            "sButtonText": "<i class='fa fa-eye'></i> Podgląd licznika",
                            "fnClick": function ( nButton, oConfig, oFlash ) {
                                tmp_arr = []; // zbieramy zaznaczone (row_selected) zgloszenia dla funkcji add_ticket
                                var mileage_id = $("#mileage-table tbody tr.row_selected td:first-child input").val();
                                if (mileage_id) {
                                    open_mileage_history(mileage_id);
                                } else { 
                                    alert("Proszę wybrać jeden licznik"); return false;
                                }
                            }
                        }
                    ]
                },
                "bStateSave": true,
                "fnStateSave": function (oSettings, oData) {
                    localStorage.setItem( 'DataTables_mileage', JSON.stringify(oData) );
                },
                "fnStateLoad": function (oSettings) {
                    return JSON.parse( localStorage.getItem('DataTables_mileage') );
                },
                "bAutoWidth": false,
        		"sAjaxSource": Urls.mileage + "/" + Device.id,
        		"aoColumns": [
                        { "mDataProp": "id", 
                            "fnRender": function ( oObj ) {
                                return '<input type=\"checkbox\" id=\"m_sel' + oObj.aData["id"] + '\" value="' + oObj.aData["id"] + '">';
                                //return o.aData[0] +' '+ o.aData[3];
                            },
                          "aTargets": [ 0 ],
                          "bSortable": false, "sWidth": "1%"
                        },
        			    { "mDataProp": "lp", "bSearchable": true, "sWidth": "10%"},
        			    { "mDataProp": "name", "bSearchable": true, "sWidth": "20%"},
        			    { "mDataProp": "state", "bSearchable": false},
                        { "mDataProp": "state_max", "bSearchable": false},
                        { "mDataProp": "state_percent", "bSearchable": false},
        		    ]
        	    });
}
