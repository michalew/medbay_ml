$(document).ready(function() {

    /* obsługa menu głównego, w górnym pasku */
    $("ul#main-menu > li:nth-child(2), ul#main-menu > li:nth-child(3), ul#main-menu > li:nth-child(4), ul#main-menu > li:nth-child(5)").hover(
    //$("ul#main-menu > li:nth-child(2)").hover(
        function() {
            var current = $(this);
            var submenu = $('ul', this);
            clearTimeout($(this).data('timeout'));
            var t = setTimeout(function() {
                submenu.show(); 
                current.addClass('active');
            }, 100);
            $(this).data('timeout', t);
        },
        function() {
            var current = $(this);
            var submenu = $('ul', this);
            var t = setTimeout(function() {
                $(submenu).fadeOut('fast'); 
                $(current).removeClass('active');
            }, 100);
            $(this).data('timeout', t);
        }
    );
    $("ul#main-menu > li:nth-child(4)").hover( function() {
        $(this).toggleClass("active");
    });
        
    /* obsługa klikania w zakładki w dolnej tabelce - serwis 
     * ładujemy odpowiednie dane ajaxem dopiero po kliknięciu w zakładkę
     */
    $("ul.device-tabs").tabs("div.panes > div", {
        current: 'active',
        onClick: function(event, i) { // ta funkcja obecnie nie jest potrzebna ale moze sie jeszcze przydac...
            //alert(i); 0 based index of clicked elememnt
            if (i >0 && event!=undefined) {
                var tabName = event.target.href.replace(/^.+?serwis[^#]*#/, '');
            } else { tabName = 'zgloszenia'; }
            if (tabName == 'zgloszenia') load_tickets(); // tabelka ze zgloszeniami
            if (tabName == 'zlecenia') load_services(); // budujemy tabelke ze zleceniami dla wybranego urzadzenia
            if (tabName == 'serwis') load_service_history();
            if (tabName == 'dokumenty') load_device_documents();
            if (tabName == 'licznik') load_mileage();
            if (tabName == 'galeria') load_device_gallery();
        }
    })

    // dashboard
    $("#home-dashboard #lcol > ul > li p").click(function() {
        $(this).parent().find('ul').toggle();
    });

    $('#home-dashboard #lcol ul li a[id^="device"]').click(function() {
        var Attr = $(this).attr("id").replace("device_", "");
        var Match = Attr.match(/(\d+)_\w+/);
        device_id = Match[1];
        window.location = "/serwis?device_id=" + device_id;
    });


    // load forms
    //Forms.add_device = $.get('/nowe-urzadzenie', "json");

    if (device_id) { Urls.devices = '/ajax/devices?device_id=' + device_id };
    if (devices_group_id) { Urls.devices = '/ajax/devices?devices_group_id=' + devices_group_id };

    /* /serwis STARTS HERE :: ładujemy główną, górną tabelkę z urządzeniami */
    load_devices();
    /* * */

});

/* cztery kolejne funkcje to ładowanie ajaxem danych do pozostałych zakladek */
function load_device_gallery() {
    $.get('/urzadzenia-galeria?id=' + Device.id, function(data) {
        $("#device-gallery").html(data);
    });
}
function load_service_history() {
    $.get('/historia-serwisowa?id=' + Device.id, function(data) {
        $("#service-history").html(data);
    });
}
function load_device_documents() {
    $.get('/dokumenty-urzadzenia?id=' + Device.id, function(data) {
        $("#device-documents").html(data);
    });
}
function load_device_instructions() {
    $.get('/dokumenty-szkolenia?id=' + Device.id, function(data) {
        $("#device-instructions").html(data);
    });
}

function add_comment(comment, object_id, user_id, content_type_id) {
    var data = {
        "comment": comment,
        "object_id": object_id,
        "user_id": user_id,
        "content_type_id": content_type_id
    };
    $.ajax({
        type: "POST",
        contentType: "application/json",
        cache: false,
        url: "/add-comment",
        data: data,
        success: function(data) {
            if (!$("dl#comments").text()) {
                $("#add_comment").after("<br><br><br><dl id=\"comments\"></dl>");
            }
            $("dl#comments").prepend(data).slice(0,1).hide().fadeIn();
        }
    });
    return false;
}
/* Get the rows which are currently selected */
function fnGetSelected( oTableLocal )
{
    var aReturn = new Array();
    var aTrs = oTableLocal.fnGetNodes();
     
    for ( var i=0 ; i<aTrs.length ; i++ )
    {
        if ( $(aTrs[i]).hasClass('row_selected') )
        {
            aReturn.push( aTrs[i] );
        }
    }
    return aReturn;
}

function fnLocalStorageReset() {
    localStorage.removeItem('DataTables');
    localStorage.removeItem('DataTables_services');
    localStorage.removeItem('DataTables_tickets');
    localStorage.removeItem('selected_devices');
}

function toggleTable(tableid) {
    var lTable = document.getElementById(tableid);
    if (lTable)
        lTable.style.display = (lTable.style.display == "table" || lTable.style.display == "") ? "none" : "table";
    var lTableToggle = document.getElementById(tableid + "_toggle");
    if (lTableToggle)
        lTableToggle.innerHTML = (lTable.style.display == "table" || lTable.style.display == "") ? "Ukryj" : "Pokaż";
    var lTableTitle = document.getElementById(tableid + "_title");
    if (lTableTitle)
        lTableTitle.className = (lTable.style.display == "table"|| lTable.style.display == "") ? "" : "collapsed";
}