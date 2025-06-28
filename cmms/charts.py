from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from datetime import datetime, date, time
from guardian.shortcuts import get_objects_for_user
from crm.models import UserProfile, CostBreakdown
from cmms.models import Ticket, Device


@login_required
def tickets(request, template="api/tickets.html"):
    """
    Ticket graph on the frontpage.
    """
    user = request.user
    # check permissions
    if not user.has_perm("cmms.view_ticket_chart"):
        raise PermissionDenied

    tickets_chart = Ticket.objects.exclude(created_ticket_date__isnull=True)
    devices = get_objects_for_user(user, "cmms.view_device", accept_global_perms=False)

    users = [user.pk]
    all_users = UserProfile.objects.all()  # get all users
    if user.is_superuser:
        users = [x.pk for x in all_users]
    else:
        locations = user.person.all()  # get all locations person is responsible for
        for location in locations:
            users += [x.pk for x in location.staff.all()]

        for u in all_users:
            if u.pk in users:
                continue
            if user.has_perm("cmms.view_all_devices"):  # nadzor techniczny
                users.append(u.pk)

    tickets_chart = tickets_chart.filter(
        Q(device__in=devices) |
        Q(person_creating__in=users) |
        Q(person_creating__isnull=True)
    ).distinct()

    tickets_chart = tickets_chart.order_by('created_ticket_date')

    today = date.today()
    today_min = datetime.combine(today, time.min)
    today_max = datetime.combine(today, time.max)
    today_tickets = tickets_chart.filter(created_ticket_date__range=(today_min, today_max)).count()

    context = {
        'tickets_chart': tickets_chart,
        'today_tickets': today_tickets,
        'user': user,
    }
    return render(request, template, context)


@login_required
def device_class(request, template="api/device_class.html"):
    """
    Device class graph on the frontpage.
    """
    if not request.user.has_perm("cmms.view_device_class_chart"):
        raise PermissionDenied

    devices_graph = Device.objects.exclude(date_manufactured__isnull=True).order_by('-date_manufactured')

    this_year = datetime.now().year
    years = [this_year - 1, this_year, this_year + 1]

    context = {
        "devices_graph": devices_graph,
        "years": years,
    }
    return render(request, template, context)


@login_required
def cost_chart(request, template="api/cost_chart.html"):
    """
    Daily costs of servicing devices
    """
    devices = get_objects_for_user(request.user, "cmms.view_device", accept_global_perms=False)
    device_pks = [device.pk for device in devices]
    costbreakdowns = CostBreakdown.objects.filter(device_id__in=device_pks)
    costs = {}

    import math

    for item in costbreakdowns:
        if item.invoice.status != 4:
            continue

        invoice_date = item.invoice.date.strftime("%m-%Y")
        try:
            costs[invoice_date] = int(math.ceil(costs[invoice_date] + item.gross_cost))
        except KeyError:
            costs[invoice_date] = int(math.ceil(item.gross_cost))

    today = datetime.now().strftime("%m-%Y")
    costs.setdefault(today, 0)

    sorted_costs = sorted(costs.items(), key=lambda x: datetime.strptime(x[0], '%m-%Y'))

    context = {
        "costs": costs,
        "sorted_costs": sorted_costs,
    }
    return render(request, template, context)
