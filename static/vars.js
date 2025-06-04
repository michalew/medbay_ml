var oTable;
var oTableTickets;
var oTableServices;
var oTableMileage;
var giRedraw = false;
var blink = false;
var new_device = false;
var device_id = false;
var devices_group_id = false;
var Device = {
    id: null,
    checkbox_clicked: null,
    saved: false,
    selected_tickets: [],
    selected_services: [],
    selected_mileage: [],
    saved_ticket: false,
    saved_service: false,
    saved_mileage: false
    //selectedService: null
}
var Forms = {
    add_ticket: null,
    edit_ticket: null,
    add_device: null,
    edit_device: null,
    add_service: null,
    edit_service: null,
    add_mileage: null,
    edit_mileage: null
}

