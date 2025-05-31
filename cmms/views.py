from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, FormView
from guardian.decorators import permission_required_or_403

# Create your views here.
from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
from guardian.shortcuts import get_objects_for_user
from cmms.models import Device, Genre, Make, Mileage, Ticket, Service
from crm.models import Invoice, Contractor, Location, CostCentre, UserProfile, Hospital
from utils.datatables import generate_datatables_records, user_name_annotation
from utils.inspection_utils import create_planned_ticket
from utils.view_mixins import AjaxView
from .forms import InspectionEventForm, InspectionForm
from .serializers import ContractorSerializer, CostCentreSerializer, LocationSerializer,InvoiceSerializer, UserProfileSerializer, HospitalSerializer, GenreSerializer, MakeSerializer, DeviceSerializer, MileageSerializer, TicketSerializer, ServiceSerializer

# Pobranie zmodyfikowanego modelu użytkownika
User = get_user_model()


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
