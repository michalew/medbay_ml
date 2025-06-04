function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i].trim();
        if (c.indexOf(name) == 0) return c.substring(name.length, c.length);
    }
    return "";
}

$(function () {
    var from = '1970-01-01',
        to = '9999-12-12';

    "use strict";

    var options = {
        events_source: '/kalendarz/wydarzenia',
        view: 'month',
        language: 'pl-PL',
        tmpl_path: '/site_media/BootstrapCalendar/tmpls/',
        tmpl_cache: false,
        onAfterEventsLoad: function (events) {
            if (!events) {
                return;
            }
            var list = $('#eventlist');
            list.html('');

            $.each(events, function (key, val) {
                $(document.createElement('tr'))
                    .html('<td class="date">' + val.start_date + ' - ' + val.end_date + '</td><td><a href="' + val.url + '">' + val.title + '</a></td>')
                    .appendTo(list);
            });
        },
        onAfterViewLoad: function (view) {
            $('.page-header h3').text(this.getTitle());
            $('.btn-group button').removeClass('active');
            $('button[data-calendar-view="' + view + '"]').addClass('active');
            var to = $('#eventlist tr:last td:first').text().split(" - ");
            if (to.length > 1){
                to = to[1];
            } else {
                to = to[0];
            }
            var from = $('#eventlist tr:first td:first').text().split(" - ");
            if (from.length > 1){
                from = from[1];
            } else {
                from = from[0];
            }
            var replaceFrom = from,
                replaceTo = to,
                reportHref = $('#generateReport'),
                hrefAttribute = reportHref.attr('href');


            if (!replaceFrom || !replaceTo) {
                reportHref.find('button').attr('disabled', 'disabled');
            } else {
                hrefAttribute = hrefAttribute.replace(from, replaceFrom);
                hrefAttribute = hrefAttribute.replace(to, replaceTo);
                from = replaceFrom;
                to = replaceTo;
                reportHref.find('button').removeAttr('disabled');
            }

            reportHref.attr('href', hrefAttribute);


        },
        classes: {
            months: {
                general: 'label'
            }
        }
    };

    var calendar = $('#calendar').calendar(options);

    $('.btn-group button[data-calendar-nav]').each(function () {
        var $this = $(this);
        $this.click(function () {
            calendar.navigate($this.data('calendar-nav'));
        });
    });

    $('.btn-group button[data-calendar-view]').each(function () {
        var $this = $(this);
        $this.click(function () {
            calendar.view($this.data('calendar-view'));
        });
    });

    $('#first_day').change(function () {
        var value = $(this).val();
        value = value.length ? parseInt(value) : null;
        calendar.setOptions({first_day: value});
        calendar.view();
    });

    $('#id_start_date').datepicker();
    $("#id_start_date").datepicker("option",
        $.datepicker.regional[ "pl" ]).datepicker("option", "dateFormat", "yy-mm-dd");

    $('#save').click(function () {
        var $note = $('form#note'),
            $modal = $('#noteModal');

        $.ajax({
            type: 'POST',
            url: '/kalendarz/wydarzenie/zapisz',
            data: {
                'title': $note.find('#id_title').val(),
                'start_date': $note.find('#id_start_date').val(),
                'csrfmiddlewaretoken': getCookie('csrftoken')
            },
            beforeSend: function () {
            },
            complete: function () {
            },
            success: function () {
                window.location.reload();
            },
            error: function (response) {

                $('form#note').replaceWith(response.responseText)
                $('#id_start_date').datepicker();
                $("#id_start_date").datepicker("option",
                $.datepicker.regional[ "pl" ]).datepicker("option", "dateFormat", "yy-mm-dd");
                return false;
            }
        });


    });

});

