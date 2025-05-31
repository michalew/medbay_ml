"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include
from django.urls.conf import re_path
from rest_framework.routers import DefaultRouter
from cmms.views import (
    CostCentreViewSet,
    LocationViewSet,
    ContractorViewSet,
    InvoiceViewSet,
    UserProfileViewSet,
    DeviceViewSet,
    MakeViewSet,
    GenreViewSet,
    TicketViewSet,
    ServiceViewSet,
    HospitalViewSet,
    MileageViewSet, ajax_tickets, ajax_services, ajax_devices, InspectionView, InspectionAddView, CreateInspectionEvents
)
from utils.widget_filter_objects import ajax_filter_services, ajax_filter_tickets, ajax_get_selected_devices, \
    ajax_get_selected_services, ajax_get_selected_tickets, ajax_filter_devices

# Router dla API v1
router = DefaultRouter()
router.register(r'v1/cost_centre', CostCentreViewSet)
router.register(r'v1/location', LocationViewSet)
router.register(r'v1/contractor', ContractorViewSet)
router.register(r'v1/invoice', InvoiceViewSet)
router.register(r'v1/userprofile', UserProfileViewSet)
router.register(r'v1/device', DeviceViewSet)
router.register(r'v1/make', MakeViewSet)
router.register(r'v1/genre', GenreViewSet)
router.register(r'v1/ticket', TicketViewSet)
router.register(r'v1/service', ServiceViewSet)
router.register(r'v1/hospital', HospitalViewSet)
router.register(r'v1/mileage', MileageViewSet)

from dane.admin import dane_admin
urlpatterns = [
    path('admin/', dane_admin.urls),
    path('api/', include(router.urls)),
    path('crm/', include('crm.urls')),
    path('koszty/', include('costs.urls')),
    path('ajax/devices', ajax_devices, name='ajax_devices'),
    path('ajax/filter-devices', ajax_filter_devices, name='ajax_filter_devices'),
    re_path(r'^ajax/tickets/(?P<did>[0-9]+)$', ajax_tickets, name='ajax_tickets'),
    path('ajax/filter-tickets', ajax_filter_tickets, name='ajax_filter_tickets'),
    re_path(r'^ajax/services/(?P<did>[0-9]+)$', ajax_services, name='ajax_services'),
    path('ajax/filter-services', ajax_filter_services, name='ajax_filter_services'),
    path('ajax/get-selected-devices', ajax_get_selected_devices, name='ajax_get_selected_devices'),
    path('ajax/get-selected-services', ajax_get_selected_services, name='ajax_get_selected_services'),
    path('ajax/get-selected-tickets', ajax_get_selected_tickets, name='ajax_get_selected_tickets'),
    path('przeglady', login_required(InspectionView.as_view()), name='inspections'),
    path('przeglady/nowy', login_required(InspectionAddView.as_view()), name='inspection-add'),
    path('utworz-zdarzenia', login_required(CreateInspectionEvents.as_view()), name='create-inspection-events'),
]

