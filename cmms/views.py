from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
from guardian.shortcuts import get_objects_for_user
from cmms.models import *
from crm.models import Invoice, Contractor, Location, CostCentre, UserProfile
from .serializers import *

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
