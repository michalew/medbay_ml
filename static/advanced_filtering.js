
$(document).ready(function(){

    $.datepicker.regional['pl'] = {
                closeText: 'Zamknij',
                prevText: '&#x3c;Poprzedni',
                nextText: 'Następny&#x3e;',
                currentText: 'Dziś',
                monthNames: ['Styczeń','Luty','Marzec','Kwiecień','Maj','Czerwiec',
                'Lipiec','Sierpień','Wrzesień','Październik','Listopad','Grudzień'],
                monthNamesShort: ['Sty','Lu','Mar','Kw','Maj','Cze',
                'Lip','Sie','Wrz','Pa','Lis','Gru'],
                dayNames: ['Niedziela','Poniedzialek','Wtorek','Środa','Czwartek','Piątek','Sobota'],
                dayNamesShort: ['Nie','Pn','Wt','Śr','Czw','Pt','So'],
                dayNamesMin: ['N','Pn','Wt','Śr','Cz','Pt','So'],
                weekHeader: 'Tydz',
                dateFormat: 'yy-mm-dd',
                firstDay: 1,
                isRTL: false,
                showMonthAfterYear: false,
                yearSuffix: ''};
    $.datepicker.setDefaults($.datepicker.regional['pl']);

    window.object_filter_is_ticket = false;
    window.object_filter_is_device = false;
    window.object_filter_is_service = false;

    window.custom_ticket_filter_m2m_id = [];
    window.custom_device_filter_m2m_id = [];
    window.custom_service_filter_m2m_id = [];

    $("#advanced_filter").click(function(){
        function check_is_empty(event){
            $(".advanced_filter_td_operator select").each(function(){
                var val = $(this).val();
                var name = $(this).attr("name");
                var field_name = name.split("_operator")[0];
                if (val != "0" && val != "7") {
                    var val_field = $("[name='"+field_name+"']").val();
                    if (!val_field || val_field=="99") {
                        $(".errors_"+field_name).text("To pole jest obowiązkowe");
                        event.preventDefault();
                    }
                } else if (val == "7") {
                    var val_field_from = $("[name='"+field_name+"_from']").val();
                    var val_field_to = $("[name='"+field_name+"_to']").val();
                    if (!val_field_from || !val_field_to) {
                        $(".errors_"+field_name).text("To pole jest obowiązkowe");
                        event.preventDefault();
                    }
                }
            });
        }
        function disabled_on_off(operator){
            var val = operator.val();
            var name = operator.attr("name");
            var field_name = name.split("_operator")[0];
            if (val != "0" && val != "7") {
                $("[name='"+field_name+"']").attr("disabled", false);
                $("[name='"+field_name+"_from']").attr("disabled", false);
                $("[name='"+field_name+"_to']").attr("disabled", false);
                $("button.filter-objects").each(function(){
                   var data_name = $(this).data("objects_name");
                   if(data_name == field_name) {
                       $(this).attr("disabled", false);
                       $("#related_"+field_name+"s_table_header").show();
                       $("."+field_name+"_selected").show();
                       $(".related_"+field_name+"s_title").show();
                   }
                });
            } else {
                $("[name='"+field_name+"']").attr("disabled", "disabled");
                $("[name='"+field_name+"_from']").attr("disabled", "disabled");
                $("[name='"+field_name+"_to']").attr("disabled", "disabled");
                $("button.filter-objects").each(function(){
                   var data_name = $(this).data("objects_name");
                   if(data_name == field_name) {
                       $(this).attr("disabled", "disabled");
                       $("#related_"+field_name+"s_table_header").hide();
                       $("."+field_name+"_selected").hide();
                       $(".related_"+field_name+"s_title").hide();
                   }
                });
            }
        }

        var list_name = $(this).data("list_name");
        $.get([location.protocol, '//', location.host, location.pathname].join('') + "get_advanced_" + list_name + "_filter/", function(data) {
            $.fancybox(data, {
                'onClosed': function(){},
                'onComplete': function(){

                    $(".search").click(function(event){
                        check_is_empty(event);
                    });

                    $("select").val("");
                    LAST_DATA_FILTER = window.LAST_DATA_FILTER;

                    $("[id^='id_date']").datepicker({ dateFormat: "yy-mm-dd" });
                    $("#id_make").autocomplete({
                       source: "get_make/"
                    });

                    $("#id_genre").autocomplete({
                       source: "get_genre/"
                    });
                    $("#id_contractor").autocomplete({
                       source: "get_contractor/"
                    });
                    $("#id_cost_centre").autocomplete({
                       source: "get_cost_centre/"
                    });


                    $("[id^='id_date'][id$='_operator']").each(function(){
                       $(this).change(function(){
                           var field_name = $(this).parent().data("field_name");
                           var val = $(this).val();
                           if (val == '6') {
                               $("#advanced_filter_table ." + field_name + "_from_to").show();
                               $("#advanced_filter_table ." + field_name).hide();
                               $("#advanced_filter_table ." + field_name).attr("disabled", "disabled");
                           } else if (val == '7') {
                               $("#advanced_filter_table ." + field_name + "_from_to").hide();
                               $("#advanced_filter_table ." + field_name).show();
                               $("#advanced_filter_table ." + field_name).attr("disabled", "disabled");
                           } else {
                               $("#advanced_filter_table ." + field_name + "_from_to").hide();
                               $("#advanced_filter_table ." + field_name).show();
                               $("#advanced_filter_table ." + field_name).attr("disabled", false);
                           }
                       });
                    });
                    for (data in LAST_DATA_FILTER) {
                      $("#id_" + data).val(LAST_DATA_FILTER[data]);

                      if (data=='cyclic' && LAST_DATA_FILTER[data] == 'on'){
                          $("#id_" + data).attr('checked', 'checked');
                      }
                      if (data == 'ticket'){
                          window.custom_ticket_filter_m2m_id = LAST_DATA_FILTER[data];
                          window.object_filter_is_ticket = true;
                      }

                      if (data == 'device'){
                          window.custom_device_filter_m2m_id = LAST_DATA_FILTER[data];
                          window.object_filter_is_device = true;
                      }

                      if (data == 'service'){
                          window.custom_service_filter_m2m_id = LAST_DATA_FILTER[data];
                          window.object_filter_is_service = true;
                      }
                    }

                    $(".advanced_filter_td_label").each(function(){
                          $(this).parents("tr").find("[id^='id_date'][id$='_operator']").each(function(){
                                   var field_name = $(this).parent().data("field_name");
                                   var val = $(this).val();
                                   if (val == '6') {
                                       $("#advanced_filter_table ." + field_name + "_from_to").show();
                                       $("#advanced_filter_table ." + field_name).hide();
                                       $("#advanced_filter_table ." + field_name).attr("disabled", "disabled");
                                   } else if (val == '7') {
                                       $("#advanced_filter_table ." + field_name + "_from_to").hide();
                                       $("#advanced_filter_table ." + field_name).show();
                                       $("#advanced_filter_table ." + field_name).attr("disabled", "disabled");
                                   } else {
                                       $("#advanced_filter_table ." + field_name + "_from_to").hide();
                                       $("#advanced_filter_table ." + field_name).show();
                                       $("#advanced_filter_table ." + field_name).attr("disabled", false);
                                   }
                            });
                    });

                    LAST_DATA_FILTER = [];
                    if (window.object_filter_is_ticket && window.custom_ticket_filter_m2m_id != '') {
                        $("#id_ticket").val(window.custom_ticket_filter_m2m_id);
                        $.get("/ajax/get-selected-tickets?ids=" + window.custom_ticket_filter_m2m_id, function(data){
                            $(".ticket_selected").remove();
                            var trs = "";
                            for (obj in data) {
                                trs += "<tr class='ticket_selected'>" +
                                    "<td><a target='_blank' href='"+data[obj]["url"]+"'>"+obj+".</a></td>" +
                                    "<td>"+data[obj]['timestamp']+"</td>" +
                                    "<td>"+data[obj]['sort']+"</td>" +
                                    "<td>"+data[obj]['description']+"</td>" +
                                    "<td>"+data[obj]['person_creating']+"</td>" +
                                    "<td>"+data[obj]['status']+"</td>" +
                                    "<td>"+data[obj]['person_closing']+"</td>" +
                                    "<td>"+data[obj]['date_closing']+"</td>" +
                                    "</tr>"
                            }
                            $("#related_tickets_table_header").after(trs);
                        }, "json");

                    }

                    if (window.object_filter_is_service && window.custom_service_filter_m2m_id != '') {
                        $("#id_service").val(window.custom_service_filter_m2m_id);
                        $.get("/ajax/get-selected-services?ids=" + window.custom_service_filter_m2m_id, function(data){
                            $("#service_selected").remove();
                            var trs = "";
                            for (obj in data) {
                                trs += "<tr class='service_selected'>" +
                                    "<td><a target='_blank' href='"+data[obj]["url"]+"'>"+obj+".</a></td>" +
                                    "<td>"+data[obj]['description_ticket']+"</td>" +
                                    "<td>"+data[obj]['sort']+"</td>" +
                                    "<td>"+data[obj]['description']+"</td>" +
                                    "<td>"+data[obj]['status']+"</td>" +
                                    "<td>"+data[obj]['person_creating']+"</td>" +
                                    "<td>"+data[obj]['contractor']+"</td>" +
                                    "<td>"+data[obj]['person_completing']+"</td>" +
                                    "<td>"+data[obj]['timestamp']+"</td>" +
                                    "</tr>"
                            }
                            $("#related_services_table_header").after(trs);
                        }, "json");

                    }

                    if (window.object_filter_is_device && window.custom_device_filter_m2m_id != '') {
                        $("#id_device").val(window.custom_device_filter_m2m_id);
                        $.get("/ajax/get-selected-devices?ids=" + window.custom_device_filter_m2m_id, function(data){
                            $("#device_selected").remove();

                            $("#related_devices_table_header").show();
                            var trs = "";
                            for (obj in data) {
                                trs += "<tr class='device_selected'>" +
                                    "<td><a target='_blank' href='"+data[obj]["url"]+"'>"+obj+".</a></td>" +
                                    "<td>"+data[obj]['inventory_number']+"</td>" +
                                    "<td>"+data[obj]['name']+"</td>" +
                                    "<td>"+data[obj]['make']+"</td>" +
                                    "<td>"+data[obj]['location']+"</td>" +
                                    "</tr>"
                            }
                            $("#related_devices_table_header").after(trs)
                        }, "json");
                    }

                    $(".advanced_filter_td_operator select").each(function(){
                        disabled_on_off($(this));
                        $(this).change(function(){
                            disabled_on_off($(this));
                        });
                    });
                }
            });
        });
    });
});
