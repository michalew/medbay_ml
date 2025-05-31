import datetime
from dateutil import relativedelta
import dateutil.parser
from cmms.models import InspectionItem, InspectionDevice, Device, Ticket
from django.contrib.auth import get_user_model

User = get_user_model()


def create_planned_ticket(request, method: str, form=None):
    request_method = request.GET if method.lower() == 'get' else request.POST

    name = request_method.get("name")
    count_planned_events = request_method.get("count_planned_events")
    cycle_value = request_method.get("cycle_value", 0)
    cycle_value_period = request_method.get("cycle_value_period", "1")
    cycle_date_start = request_method.get("cycle_date_start")
    recurring_time = request_method.get("recurring_time")
    recurring_period = request_method.get("recurring_period")

    events = []
    devices = request_method.getlist("device")

    if form:
        inspection = form.save(commit=False)
        inspection.added_user = request.user
        inspection.save()
        for device_pk in devices:
            try:
                device_obj = Device.objects.get(pk=int(device_pk))
                InspectionDevice.objects.create(inspection=inspection, device=device_obj)
            except (Device.DoesNotExist, ValueError):
                pass

    days_planned_date = 0
    months_planned_date = 0

    if cycle_value:
        try:
            cycle_value_int = int(cycle_value)
        except (TypeError, ValueError):
            cycle_value_int = 0
        if cycle_value_period == '1':
            days_planned_date = cycle_value_int
        elif cycle_value_period == '2':
            days_planned_date = cycle_value_int * 7
        elif cycle_value_period == '3':
            months_planned_date = cycle_value_int
        elif cycle_value_period == '4':
            months_planned_date = 12 * cycle_value_int

    days_recurring = 0
    months_recurring = 0
    if recurring_period == '1':
        try:
            days_recurring = int(recurring_time)
        except (TypeError, ValueError):
            days_recurring = 0
    elif recurring_period == '2':
        try:
            months_recurring = int(recurring_time)
        except (TypeError, ValueError):
            months_recurring = 0

    next_ticket_planned_date = dateutil.parser.parse(cycle_date_start) if cycle_date_start else datetime.datetime.now()

    for i in range(int(count_planned_events) if count_planned_events else 0):
        if i > 0:
            if days_planned_date:
                next_ticket_planned_date += relativedelta.relativedelta(days=days_planned_date)
            elif months_planned_date:
                next_ticket_planned_date += relativedelta.relativedelta(months=months_planned_date)

        if days_recurring:
            next_ticket_date = next_ticket_planned_date - relativedelta.relativedelta(days=days_recurring)
        elif months_recurring:
            next_ticket_date = next_ticket_planned_date - relativedelta.relativedelta(months=months_recurring)
        else:
            next_ticket_date = next_ticket_planned_date

        if form:
            inspection_item = InspectionItem(
                inspection=inspection,
                name=name,
                planned_date=next_ticket_planned_date,
                ticket_date=next_ticket_date,
                added_user=request.user
            )
            inspection_item.save()
        else:
            one_event = {
                "name": name,
                "date_planned": next_ticket_planned_date,
                "date_ticket": next_ticket_date
            }
            events.append(one_event)

    if form:
        create_tickets_from_inspection(inspection=inspection, user=request.user)
    return events


def create_tickets_from_inspection(inspection=None, user=None):
    if inspection:
        # Ticket.objects.filter(status=6, from_which_inspection=inspection).delete()
        items = InspectionItem.objects.filter(inspection=inspection)

        if not user:
            user_qs = User.objects.filter(is_superuser=True)
            user = user_qs.first() if user_qs.exists() else None

        for item in items:
            ticket, created = Ticket.objects.get_or_create(from_which_inspection_item=item)
            ticket.sort = 2
            ticket.status = 6
            ticket.cyclic = True
            ticket.description = item.name
            if user:
                ticket.person_creating = user
            ticket.planned_date_execute = item.planned_date
            ticket.inspection_type = item.inspection.type
            ticket.from_which_inspection = item.inspection
            ticket.from_which_inspection_item = item
            ticket.timestamp = item.ticket_date
            ticket.person_creating = item.added_user
            ticket.save()

            devices = InspectionDevice.objects.filter(inspection=item.inspection).values_list('device', flat=True)
            if devices:
                ticket.device.set(devices)
            ticket.save()

            item.created_ticket_id = ticket.pk
            item.save(stop_create_tickets=True)
