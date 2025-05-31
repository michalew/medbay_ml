$(document).ready(function () {

    $('#id_start_date').datepicker();
    $("#id_start_date").datepicker("option",
        $.datepicker.regional[ "pl" ]).datepicker("option", "dateFormat", "yy-mm-dd").datepicker(
            "option", "monthNames", [ "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec",
                "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień" ] );
    $('#id_end_date').datepicker();
    $("#id_end_date").datepicker("option",
        $.datepicker.regional[ "pl" ]).datepicker("option", "dateFormat", "yy-mm-dd").datepicker(
            "option", "monthNames", [ "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec",
                "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień" ] );

    $('#costs_range button').click(function () {
        var data = {
                'device_id': $('#id_device_id').val(),
                'start_date': $('#id_start_date').val(),
                'end_date': $('#id_end_date').val(),
                'csrfmiddlewaretoken': getCookie('csrftoken')
            },
            url = '/koszty/zakres?' + $.param(data);

         $.ajax({
            type: 'POST',
            url: url,
            data: data,
            beforeSend: function () {
            },
            complete: function () {
            },
            success: function (response) {
                $('#range').replaceWith(response);
                return false;
            },
            error: function (response) {
                $('#range').replaceWith(response);
                return false;
            }
        });

        return false;
    });
});

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i].trim();
        if (c.indexOf(name) == 0) return c.substring(name.length, c.length);
    }
    return "";
}
