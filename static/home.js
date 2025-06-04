function preview_device_id(device_id) { // funckja udpalana jako callback dla przycisku "podgląd urządzenia"

    // jeśli edycja podgląd (edycja) urządzenia to ładujemy formularz wypełniony danymi urządzenia
    var form; var form_url;
    form_url = "/podglad-urzadzenia?id=" + device_id;

    $.get(form_url, function(data) { // pobieramy ajaxem formularz
        $.fancybox( // żeby ładnie było
            data, {}
        );

    }).done( function() {
        $(".print").on("click", function() { 
            $(".action-form").printElement();
        });
        $(".print-device").on("click", function() {
            generate_pdf_directly("device", device_id);
        });
    });
}
