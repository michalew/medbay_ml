from django.contrib.auth import get_user_model
from rest_framework import serializers
from cmms.models import Genre, Make, Mileage, Ticket, Service, Device
from crm.models import Invoice, Contractor, Location, CostCentre, UserProfile, Hospital

# Pobranie zmodyfikowanego modelu użytkownika
User = get_user_model()


class CostCentreSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCentre
        fields = '__all__'


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'


class ContractorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contractor
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User  # Używamy zmodyfikowanego modelu użytkownika
        exclude = ['password', 'is_superuser', 'is_staff', 'is_active']


class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = '__all__'


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = '__all__'


class MakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Make
        fields = '__all__'


class DeviceSerializer(serializers.ModelSerializer):
    genre = GenreSerializer()
    make = MakeSerializer()
    cost_centre = CostCentreSerializer()
    location = LocationSerializer()
    person_responsible = UserProfileSerializer()
    technical_supervisor = UserProfileSerializer()
    contractor = ContractorSerializer()

    class Meta:
        model = Device
        fields = '__all__'


class MileageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mileage
        fields = '__all__'



class TicketSerializer(serializers.ModelSerializer):
    person_creating = serializers.HyperlinkedRelatedField(
        queryset=UserProfile.objects.all(),
        view_name='userprofile-detail'
    )
    device = serializers.HyperlinkedRelatedField(
        many=True,
        queryset=Device.objects.all(),
        view_name='device-detail'
    )

    created_ticket_date = serializers.DateTimeField(read_only=True)
    timestamp = serializers.DateField(read_only=True)
    date_closing = serializers.DateField(read_only=True)
    date_finish = serializers.DateField(read_only=True)
    planned_date_finish = serializers.DateField(read_only=True)
    planned_date_execute = serializers.DateField(read_only=True)
    date_execute = serializers.DateField(read_only=True)

    class Meta:
        model = Ticket
        fields = '__all__'


class ServiceSerializer(serializers.ModelSerializer):
    ticket = TicketSerializer(many=True)
    person_assigned = UserProfileSerializer()
    person_creating = UserProfileSerializer()
    contractor = ContractorSerializer()
    person_completing = UserProfileSerializer()
    hospital = HospitalSerializer()

    class Meta:
        model = Service
        fields = '__all__'
