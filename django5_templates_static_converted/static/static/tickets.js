$(document).ready(function() {
    // check all, uncheck all
    $("#tickets-table thead #t_selall").click(function() {
            $("#tickets-table tbody input:checkbox").prop("checked", $(this).prop("checked"));
        });

    $('#tickets-table tbody').on("click", "tr td input", function(event) {
        // manage selected ticket for current device (Device.selected_tickets)
        var ticket_id = $(this).val();
        if ($(this).prop("checked")) {
            Device.selected_tickets.push(ticket_id);
        } else {
            var arr_index = $.inArray(ticket_id, Device.selected_tickets);
            if (arr_index>-1) Device.selected_tickets.splice(arr_index, 1);
        }
        // ticket table multiple rows selected
        //$(this).toggleClass('row_selected');
    });

    $("#tickets-table tbody").click(function(event) {
        var checkbox_clicked = event.target.id.match(/t_sel\d+/); // sprwdzamy czy kliknieto w checkbox, jesli nie to Device.checkbox_clicked == null ...
        if (checkbox_clicked == null) { // kliknieto w row (nie w checkbox) wiec zaznaczamy row (row_selected)
            $("#tickets-table tr.row_selected").removeClass('row_selected');
            $(event.target.parentNode).addClass('row_selected');
        }
    });

    $(".headerTicketBtn").click(function () {
        var deviceId = $(this).attr("data-device");
        var arr = deviceId ? [deviceId] : false;
        add_ticket(arr);
    });
});

function add_ticket(arr, edit) { // funckja udpalana jako callback dla przycisku "dodaj zgłoszenie"

    var form; var form_url;
    if (edit) {
        form_url = "/nowe-zgloszenie?id=" + Device.selected_tickets[0];
        if (!(Device.selected_tickets[0])) form_url = "/nowe-zgloszenie?id=" + arr[0];
    } else { 
        form_url = "/nowe-zgloszenie";
    }
        

    $.get(form_url, function(data) {
        $.fancybox(
            data,
            {
                'onClosed': function() {
                    if (oTableTickets && Device.saved_ticket) { 
                        Device.saved_ticket = false; 
                        var st_arr = Device.selected_tickets;
                        for (var t in st_arr) {
                            //$("#tickets-table tr td:first-child:contains('" + st_arr[t] + "')").parent().addClass('row_selected');
                            $("#tickets-table tr td:first-child").each( function() {
                                var _id = $(this).text();
                                if (_id == st_arr[t]) $(this).parent().addClass('row_selected');
                            });
                        }
                    }
                }
            }
            );
        
        $("#device" + Device.id).css("font-weight", "bold"); // zaznaczamy wybrane urzadzenie w warning-info (form)

        $("#add-ticket").on("submit", function() {
    
            $.fancybox.showActivity();
            
            var comment = $("#id_comment").val();
            if (comment) {
                _comment = add_comment(comment, Device.selected_tickets[0], User.id, 34); // 34 - ticket content type
            }

            if (edit) arr = $("input[name=devices_id_list]").val().split(","); // jesli edytujemy to id_urzadzen bierzemy z forma
            var device_arr = Array();
            for (var i in arr) {
                device_arr.push("/api/v1/device/" + arr[i] + "/");   
            }
            var data = JSON.stringify({
                    "sort": $("#id_sort").val(),
                    "cyclic": $("#id_cyclic:checked").val(),
                    "description": $("#id_description").val(),
                    "status": $("#id_status").val(),
                    "person_creating": "/api/v1/userprofile/" + User.id + "/",
                    "device": device_arr
                })
    
            // add or edit ...
            var request_type = "POST";
            if (edit) request_type = "PUT";
            var request_url = "/api/v1/ticket/";
            if (edit) request_url = "/api/v1/ticket/" + Device.selected_tickets[0] + "/";
            var msg_success = "Wysłano zgłoszenie dla wybranych urządzeń.";
            if (edit) msg_success = "Zaktualizowano zgłoszenie";

            $.ajax({
                type: request_type,
                contentType: "application/json",
                cache: false,
                url: request_url,
                data: data,
                success: function(data) {
                    $(".action-form h1").html(msg_success);
                    $("#add-ticket input, #add-ticket select, #add-ticket textarea").prop("disabled", true);
                    $("#add-ticket #submit-row").hide();
                    $.fancybox.hideActivity();
                    Device.saved_ticket = true;
                    oTableTickets.fnDraw(false); 
                }
            });
            
            return false;
    
    
        }); // end of #add-ticket submit bind... 

    }).fail( 
        function(jqXHR, textStatus){ 
            if (jqXHR.status == 403) 
                alert("Brak wymaganych uprawnień!"); 
            else
                alert("Wystąpił błąd."); 
        }); // end of load form callback: $.get(form_url ....

}

function preview_ticket(arr) { // funckja odpalana jako callback dla przycisku "podgląd zgłoszenia"
    var form; var form_url;
    form_url = "/podglad-zgloszenia/" + arr;

    $.get(form_url, function(data) {
        $.fancybox(
            data, { }
            );

    }); // end of load form callback: $.get(form_url ....

}

function load_tickets() { // funkcja odpalana gdy wybierzemy urzadzenie - buduje tabelke ze zleceniami tego urzadzenia
    if (Device.id){
            if (oTableTickets!==undefined) {
                //oTableTickets.fnClearTable();
                oTableTickets.fnDestroy();
            }
            oTableTickets = $('#tickets-table').dataTable({
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
                    "sButtonText": "<i class='fa fa-plus-circle'></i> Dodaj zlecenie",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        if (window.user_group_permissions.indexOf("cmms.add_service") < 0) {
                            alert("Brak wymaganych uprawnień!");
                            return false;
                        }
                        tmp_arr = []; // zbieramy zaznaczone (row_selected) zgloszenia dla funkcji add_service
                        $("#tickets-table tbody tr td input:checked").each(function(index) { tmp = parseInt($(this).val()); tmp_arr.push(tmp); });
                        if (tmp_arr.length > 0) { add_service(tmp_arr); } else { alert("Proszę wybrać przynajmniej jedno zgłoszenie"); return false; } //TODO: nie mozna dodac zlecenia do ticketa ,ktory ma otwarte zlecenie?
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "<i class='fa fa-file-excel-o'></i> Eksportuj do XLS",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        tmp_arr = [];
                        $("#tickets-table tbody input:checked").each(function(index) { tmp = $(this).val(); tmp_arr.push(tmp); });
                        if (tmp_arr.length > 0) { generate_xls('Ticket', tmp_arr); } else { alert("Proszę wybrać przynajmniej jedno zgłoszenie"); return false; }
                    }
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "<i class='fa fa-pencil'></i> Edytuj zgłoszenie",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        tmp_arr = []; // zbieramy zaznaczone (row_selected) zgloszenia dla funkcji add_ticket
                        var ticket_id = $("#tickets-table tbody tr.row_selected td:first-child input").val();
                        var ticket_status = $("#tickets-table tbody tr.row_selected td:last-child").contents()[0].data;
                        
                        // sprawdzamy czy zgłoszenie jest zamknięte
                        if (ticket_status == "Zamknięte" && !window.is_superuser) {
                            alert("Nie można edytować zgłoszeń o statusie: ZAMKNIĘTE.");
                            return false;
                        }
                        
                        if (ticket_id) {
                            window.open("/a/cmms/ticket/" + ticket_id + "/");
                        } else { 
                            alert("Proszę wybrać jedno zgłoszenie"); return false;
                        }
                    },
                },
                {
                    "sExtends":    "select",
                    "sButtonText": "<i class='fa fa-eye'></i> Podgląd zgłoszenia",
                    "fnClick": function ( nButton, oConfig, oFlash ) {
                        tmp_arr = []; // zbieramy zaznaczone (row_selected) zgloszenia dla funkcji add_ticket
                        var ticket_id = $("#tickets-table tbody tr.row_selected td:first-child input").val();
                        if (ticket_id) {
                            preview_ticket(ticket_id); 
                        } else { 
                            alert("Proszę wybrać jedno zgłoszenie"); return false;
                        }
                    }
                },
            ]
            },
            "bStateSave": true,
            "fnStateSave": function (oSettings, oData) {
                localStorage.setItem( 'DataTables_tickets', JSON.stringify(oData) );
            },
            "fnStateLoad": function (oSettings) {
                return JSON.parse( localStorage.getItem('DataTables_tickets') );
            },
            "bAutoWidth": false,
            "sAjaxSource": Urls.tickets + "/" + Device.id,
            "aaSorting": [[ 1, "desc" ]], // sort by id/lp
            "aoColumns": [
                    { "mDataProp": "id", 
                        "fnRender": function ( oObj ) {
                            return '<input type=\"checkbox\" id=\"t_sel' + oObj.aData["id"] + '\" value="' + oObj.aData["id"] + '">';
                            //return o.aData[0] +' '+ o.aData[3];
                        },
                      "aTargets": [ 0 ],
                      "bSortable": false, "sWidth": "1%"
                    },
                    { "mDataProp": "lp", "bSearchable": true, "sWidth": "10%"},
                    { "mDataProp": "timestamp", "bSearchable": true, "sWidth": "20%"},
                    { "mDataProp": "sort", "bSearchable": false, "bSortable": true},
                    { "mDataProp": "description", "bSearchable": true},
                    { "mDataProp": "person_creating", "bSearchable": false},
                    { "mDataProp": "status", "bSearchable": false}
                ]
        });
    }
}