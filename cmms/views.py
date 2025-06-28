import datetime

from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, FormView
from guardian.decorators import permission_required_or_403
from django_sendfile import sendfile# Create your views here.
from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
from guardian.shortcuts import get_objects_for_user
from cmms.models import Device, Genre, Make, Mileage, Ticket, Service, DevicePassport, TicketForm, Document
from crm.models import Invoice, Contractor, Location, CostCentre, UserProfile, Hospital
from utils.datatables import generate_datatables_records, user_name_annotation
from utils.inspection_utils import create_planned_ticket
from utils.view_mixins import AjaxView
from .forms import InspectionEventForm, InspectionForm, PassportManagerForm
from .serializers import ContractorSerializer, CostCentreSerializer, LocationSerializer,InvoiceSerializer, UserProfileSerializer, HospitalSerializer, GenreSerializer, MakeSerializer, DeviceSerializer, MileageSerializer, TicketSerializer, ServiceSerializer
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from guardian.shortcuts import get_objects_for_user
from django.http import HttpResponse, Http404
from guardian.shortcuts import get_objects_for_user
from django.core.exceptions import PermissionDenied

# Pobranie zmodyfikowanego modelu użytkownika
User = get_user_model()


@login_required
def home(request):
    try:
        user = UserProfile.objects.get(username=request.user.username)
    except UserProfile.DoesNotExist:
        user = request.user

    can_view_all_devices = user.has_perm('cmms.view_all_devices')

    usr_locations = []

    groups = list(user.groups.values_list('name', flat=True))
    user_groups = ", ".join(groups)

    devices_all = get_objects_for_user(
        user, "cmms.view_device", accept_global_perms=False)
    devices_all_count = devices_all.count()

    devices_broken = devices_all.filter(status=4)
    devices_broken_count = devices_broken.count()

    latest_tickets = Ticket.objects.filter(
        Q(status__in=[0, 1]) &
        (Q(person_creating=request.user) | Q(device__in=devices_all))
    ).order_by('-timestamp').distinct()

    arr = list(latest_tickets.values_list('pk', flat=True))

    opened_services = Service.objects.filter(
        status__in=[0, 1], ticket__id__in=arr).order_by('-timestamp')
    opened_services_count = opened_services.count()

    # check if we need to display "Zobacz wszystkie" link
    show_more_devices_link = devices_all_count > 15
    if show_more_devices_link:
        devices_all = devices_all[:15]

    show_more_broken_link = devices_broken_count > 15
    if show_more_broken_link:
        devices_broken = devices_broken[:15]

    show_more_services_link = opened_services_count > 15
    if show_more_services_link:
        opened_services = opened_services[:15]

    show_more_tickets_link = latest_tickets.count() > 15
    if show_more_tickets_link:
        latest_tickets = latest_tickets[:15]

    context = locals()
    return render(request, 'home.html', context)


class CostCentreViewSet(viewsets.ModelViewSet):
    queryset = CostCentre.objects.all()
    serializer_class = CostCentreSerializer
    permission_classes = [permissions.DjangoModelPermissions]


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        usr_locations = user.staff.all() | user.person.all()
        usr_location_ids = [loc.pk for loc in usr_locations]

        if user.has_perm("cmms.change_location"):
            return Location.objects.all()
        else:
            return Location.objects.filter(pk__in=usr_location_ids)


class ContractorViewSet(viewsets.ModelViewSet):
    queryset = Contractor.objects.all()
    serializer_class = ContractorSerializer
    permission_classes = [permissions.DjangoModelPermissions]


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.DjangoModelPermissions]


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()  # Dodaj to
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if user.has_perm("crm.change_userprofile"):
            return User.objects.all()
        else:
            return User.objects.filter(pk=user.pk)


class HospitalViewSet(viewsets.ModelViewSet):
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    permission_classes = [permissions.AllowAny] #dla testów w Postman


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [permissions.DjangoModelPermissions]


class MakeViewSet(viewsets.ModelViewSet):
    queryset = Make.objects.all()
    serializer_class = MakeSerializer
    permission_classes = [permissions.DjangoModelPermissions]


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [permissions.DjangoModelPermissions]

    # Dodanie logiki, jeśli jest wymagane filtrowanie
    def get_queryset(self):
        # Zastosowanie uprawnień lub filtrowania na podstawie użytkownika
        return Device.objects.all()


class MileageViewSet(viewsets.ModelViewSet):
    queryset = Mileage.objects.all()
    serializer_class = MileageSerializer

    def get_queryset(self):
        user = self.request.user
        devices = get_objects_for_user(user, "cmms.view_device", accept_global_perms=False)
        return Mileage.objects.filter(device__in=devices)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.DjangoModelPermissions]


    def get_queryset(self):
        user = self.request.user
        devices = get_objects_for_user(user, "cmms.view_device", accept_global_perms=False)
        return Ticket.objects.filter(device__in=devices).distinct()


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        devices = get_objects_for_user(user, "cmms.view_device", accept_global_perms=False)
        tickets = Ticket.objects.filter(device__in=devices).distinct()
        return Service.objects.filter(ticket__in=tickets).distinct()


def ajax_devices(request):
    # do not prepare data in view (as in  above view), data will be retrieved
    # using ajax call (see get_countries_list below).

    # initial querySet
    device_id = request.GET.get("device_id", None)
    devices_group_id = request.GET.get("devices_group_id", None)

    querySet = get_objects_for_user(
        request.user, "cmms.view_device", accept_global_perms=False).annotate(
        person_responsible_n=user_name_annotation("person_responsible"),
        technical_supervisor_n=user_name_annotation("technical_supervisor")
    )

    if device_id:  # TODO zrobic na filtrze (id=168) ?
        querySet = querySet.filter(pk=int(device_id))
    if devices_group_id:
        querySet = querySet.filter(group__exact=int(devices_group_id))

    columnIndexNameMap = {
        'lp': 'id',
        'location': 'location__name',
        'person_responsible': 'person_responsible_n',
        'technical_supervisor': 'technical_supervisor_n',
    }

    # path to template used to generate json
    return generate_datatables_records(request, querySet, columnIndexNameMap,
                                       'datatables/json_devices.txt')


def ajax_tickets(request, did):
    # do not prepare data in view (as in  above view), data will be retrieved
    # using ajax call (see get_countries_list below).
    # initial querySet
    querySet = Ticket.objects.filter(device__id=did).annotate(
        person_creating_n=user_name_annotation("person_creating")
    )
    columnIndexNameMap = {
        'lp': 'id',
        'person_creating': 'person_creating_n',
    }

    # call to generic function from utils
    return generate_datatables_records(
        request, querySet, columnIndexNameMap, 'datatables/json_tickets.txt')


def ajax_services(request, did):
    tickets = Ticket.objects.filter(device__id=did)
    querySet = Service.objects.filter(ticket__in=tickets).annotate(
        person_assigned_n=user_name_annotation("person_assigned"),
        person_creating_n=user_name_annotation("person_creating"),
        person_completing_n=user_name_annotation("person_completing")
    )
    columnIndexNameMap = {
        'lp': 'id',
        "ticket": "ticket__device__name",
        'person_assigned': 'person_assigned_n',
        'person_creating': 'person_creating_n',
        'person_completing': 'person_completing_n',
    }

    return generate_datatables_records(
        request, querySet, columnIndexNameMap, 'datatables/json_services.txt')

@method_decorator(permission_required_or_403('cmms.view_changelist_inspection'), name='dispatch')
class InspectionView(TemplateView):
    template_name = "inspections/inspections.html"


class InspectionAddView(AjaxView, FormView):
    template_name = "inspections/new_inspection.html"
    form_class = InspectionForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        selected_devices = self.request.GET.get('devices')
        devices = []
        if selected_devices:
            devices = [int(device) for device in selected_devices.split(",") if device]

        context['devices'] = Device.objects.filter(pk__in=devices)
        return context

    def form_valid(self, form):
        create_planned_ticket(self.request, "post", form)
        return JsonResponse({'save': True})

    def form_invalid(self, form):
        errors = {field: error[0] for field, error in form.errors.items()}
        return JsonResponse(errors, status=400)


class CreateInspectionEvents(AjaxView, TemplateView):
    template_name = "inspections/new_inspection.html"  # podaj właściwą ścieżkę do szablonu

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = InspectionEventForm(self.request.GET)
        if form.is_valid():
            events = create_planned_ticket(self.request, "get")
            planned_events_table = render_to_string(
                "inspections/planned_tickets.html", {"events": events}
            )
            context["planned_events_table"] = planned_events_table
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            context["errors"] = errors

        return context

def passport_manager(request):
    model_name = request.GET.get("model")
    if model_name not in ("service", "ticket"):
        raise Http404("Invalid model name")

    if model_name == "service":
        model = Service
        model_verbose_name = "zlecenia"
    else:  # model_name == "ticket"
        model = Ticket
        model_verbose_name = "zgłoszenia"

    object_id = request.GET.get("obj")
    if not object_id:
        raise Http404("Object ID not provided")

    obj = get_object_or_404(model, pk=object_id)

    # devices
    if model_name == "service":
        devices = []
        for ticket in obj.ticket.all():
            devices.extend(ticket.device.all())
    else:  # ticket
        devices = list(obj.device.all())

    accessible_devices = [d for d in devices if device_access_check(request.user, d.pk)]

    added_date = datetime.now()

    if model_name == "ticket":
        if obj.date_execute:
            added_date = obj.date_execute
    else:  # service
        new_added_date = None
        for ticket in obj.ticket.all():
            if ticket.date_execute:
                if not new_added_date or ticket.date_execute > new_added_date:
                    new_added_date = ticket.date_execute
        if new_added_date:
            added_date = new_added_date

    if request.method == "POST":
        form = PassportManagerForm(request.POST)

        if not request.user.has_perm("cmms.add_devicepassport"):
            raise PermissionDenied

        if form.is_valid():
            is_service = form.cleaned_data.get("is_service", False)
            selected_devices = form.cleaned_data["devices"].split(",")

            device_objects = [d for d in accessible_devices if str(d.pk) in selected_devices]
            # failed_device_objects not used, can be removed or logged if needed

            passport_text = form.cleaned_data["text"]

            for device in device_objects:
                passport, created = DevicePassport.objects.get_or_create(
                    device=device,
                    defaults={
                        "content": passport_text,
                        "added_user": request.user,
                        "added_date": added_date,
                    }
                )
                if not created:
                    # Update fields if object existed
                    passport.content = passport_text
                    passport.added_user = request.user
                    passport.added_date = added_date
                    passport.save()

                if is_service:
                    device.date_service = added_date
                    device.save()

            is_submitted = True
    else:
        company_name = "[nazwa firmy]"
        if getattr(obj, "contractor", None):
            company_name = obj.contractor
        if getattr(obj, "contractor_execute", None):
            company_name = obj.contractor_execute

        person_execute = "[osoba wykonująca czynności serwisowe]"
        sort = "[naprawę | przegląd okresowy]"

        TICKET_SORT_ALTFORMS = {
            0: "sprawdzenie",
            1: "naprawę",
            2: "przegląd",
            3: "sprawdzenie bezpieczeństwa",
            4: "aktualizację oprogramowania",
            5: "legalizację",
            6: "wzorcowanie",
            7: "konserwację",
        }

        if model_name == "ticket":
            if getattr(obj, "person_execute", None):
                person_execute = obj.person_execute
            if getattr(obj, "sort", None) is not None:
                sort = TICKET_SORT_ALTFORMS.get(obj.sort, sort)

        filled_template = (
            f"Wykonano {sort} zgodnie z zaleceniami producenta.\n"
            "Wymieniono: [podać części zamienne].\n"
            "Nr protokołu serwisowego: [podać nr protokołu].\n"
            "Sprzęt [sprawny | niesprawny | warunkowo dopuszczony do eksploatacji].\n"
            "Zalecenia serwisowe: [podać zalecenia].\n"
            "Data następnej czynności serwisowej: [podać przybliżoną datę].\n\n"
            f"{person_execute} / {company_name}\n"
            f"Nr powiązanego {model_verbose_name} #{obj.pk}"
        )

        form = PassportManagerForm(initial={"text": filled_template, "is_service": model_name == "ticket"})
        is_submitted = False

    context = {
        "form": form,
        "is_submitted": locals().get("is_submitted", False),
        "model_name": model_name,
        "obj": obj,
        "model_verbose_name": model_verbose_name,
        "accessible_devices": accessible_devices,
    }

    return render(request, "passport-manager.html", context)


@login_required
def new_ticket(request):
    ticket_id = request.GET.get('id')
    ticket = None
    devices = None

    if ticket_id:
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        devices = ticket.device.all()
        form = TicketForm(instance=ticket)
    else:
        form = TicketForm()

    if ticket:
        our_devices = get_objects_for_user(
            request.user, 'cmms.view_device', accept_global_perms=False
        )
        matches = [x for x in devices if x in our_devices]
        if not matches:
            raise PermissionDenied
    else:
        if not request.user.has_perm('cmms.add_ticket'):
            raise PermissionDenied

    context = {
        'ticket': ticket,
        'devices': devices,
        'form': form,
    }
    return render(request, 'new-ticket.html', context)

@login_required
def preview_device(request):
    device_id = request.GET.get('id')
    if not device_id:
        raise Http404()

    if not device_access_check(request.user, device_id):
        raise PermissionDenied

    device = get_object_or_404(Device, pk=int(device_id))

    if not request.user.has_perm('cmms.view_device', device):
        raise PermissionDenied

    context = {
        'device': device,
    }
    return render(request, 'device-preview.html', context)


@login_required
def ticket_preview(request, ticket_id):
    devices = get_objects_for_user(
        request.user, 'cmms.view_device', accept_global_perms=False)
    tickets = Ticket.objects.filter(device__in=devices).distinct()

    ticket = get_object_or_404(tickets, pk=ticket_id)

    # check if user has permissions for viewing this form
    # (get_object_or_404 already raises 404 if not found)
    # If you want to check additional permission, do it here:
    # if not request.user.has_perm('some_permission', ticket):
    #     raise PermissionDenied

    context = {
        'ticket': ticket,
    }
    return render(request, 'ticket-preview.html', context)


@login_required
def service_preview(request, service_id):
    devices = get_objects_for_user(
        request.user, 'cmms.view_device', accept_global_perms=False)
    tickets = Ticket.objects.filter(device__in=devices).distinct()
    services = Service.objects.filter(ticket__in=tickets).distinct()

    service = get_object_or_404(services, pk=service_id)

    # check if user has permissions for viewing this form
    # if not request.user.has_perm('some_permission', service):
    #     raise PermissionDenied

    context = {
        'service': service,
    }
    return render(request, 'service-preview.html', context)


@login_required
def mileage_preview(request, mileage_id):
    mileage = get_object_or_404(Mileage, pk=mileage_id)

    # check permissions for device
    if not device_access_check(request.user, mileage.device.id):
        raise PermissionDenied

    history = mileage.history.all().order_by('-pk')

    context = {
        'mileage': mileage,
        'history': history,
    }
    return render(request, 'mileage-preview.html', context)

@login_required
def ajax_inspections(request):
    devices = get_objects_for_user(
        request.user, "cmms.view_device", accept_global_perms=False
    )

    queryset = devices.filter(Q(ticket__sort=2) | Q(ticket__sort=7)).order_by('-id').distinct().annotate(
        ticket_id=F("ticket__pk"),
        person_execute=user_name_annotation("ticket__person_execute"),
    ).annotate(**{
        field.split("__")[0]: F(f"ticket__{field}")
        for field in [
            "from_which_inspection",
            "planned_date_execute",
            "inspection_type",
            "date_execute",
            "contractor_execute__name",
            "description",
        ]
    })

    columnIndexNameMap = {"lp_device": "id"}

    return generate_datatables_records(
        request, queryset, columnIndexNameMap, 'datatables/json_inspections.txt'
    )


@login_required
def download_document(request, document_id):
    """Downloads a document with given ID"""
    document = get_object_or_404(Document.objects.for_user(request.user), pk=document_id)
    if document.scan:
        return sendfile(request, document.scan.path)
    raise Http404()


def device_access_check(user, device_id):
    """
    Returns True if user has access to device, otherwise False.
    """
    if device_id and user and user.is_authenticated:
        devices = get_objects_for_user(
            user, "cmms.view_device", accept_global_perms=False
        )
        return devices.filter(pk=int(device_id)).exists()
    return False