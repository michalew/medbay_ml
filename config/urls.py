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
from django.contrib.auth import views as auth_views, logout
from django.shortcuts import redirect
from django.urls import path, include
from django.urls.conf import re_path
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static


import cmms
import utils
from cmms import charts
from cmms.views import (
    home,
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
    MileageViewSet, ajax_tickets, ajax_services, ajax_devices, InspectionView, InspectionAddView,
    CreateInspectionEvents, generate_qrcodes, MobileDeviceView
)
from utils.views import PDFPreview, PDFGenerate, PDFGenerateDirectly, GenerateXLSPreview, GenerateXLS
from utils.widget_filter_objects import ajax_filter_services, ajax_filter_tickets, ajax_get_selected_devices, \
    ajax_get_selected_services, ajax_get_selected_tickets, ajax_filter_devices
from reminders import urls as reminders_urls

class LogoutGetAllowedView(auth_views.LogoutView):
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect(self.next_page or '/')

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
    path('a/', dane_admin.urls),
    path('login/', auth_views.LoginView.as_view(template_name='admin/login.html'), name='login'),
    path('logout/', LogoutGetAllowedView.as_view(template_name= 'registration/logged_out.html'), name='logout'),
    path('', home, name='home'),
    path('serwis', cmms.views.devices, name='devices'),

    path('api/', include(router.urls)),
    path('api/ticket-graph/', charts.tickets, name='api_tickets_chart'),
    re_path(r'^api/device-class/$', charts.device_class, name="api_device_class_chart"),
    re_path(r'^api/cost-graph/$', charts.cost_chart, name="api_cost_chart"),
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
    path('kalendarz/', include(reminders_urls)),
    path('przeglady/nowy', login_required(InspectionAddView.as_view()), name='inspection-add'),
    path('utworz-zdarzenia', login_required(CreateInspectionEvents.as_view()), name='create-inspection-events'),
    path('get_filter_devices', utils.widget_filter_objects.get_filter_devices, name='get_filter_devices'),
    path('get_filter_tickets', utils.widget_filter_objects.get_filter_tickets, name='get_filter_tickets'),
    path('get_filter_services', utils.widget_filter_objects.get_filter_services, name='get_filter_services'),
    path('get_filter_external_services', utils.widget_filter_objects.get_filter_external_services, name='get_filter_external_services'),
    path('mobile/device/<int:pk>/', MobileDeviceView.as_view(), name='mobile_device'),

    re_path(r'^podglad-urzadzenia$', cmms.views.preview_device),
    re_path(r'^podglad-zgloszenia/(?P<ticket_id>[0-9]+)$', cmms.views.ticket_preview, name='ticket_preview'),
    re_path(r'^podglad-zlecenia/(?P<service_id>[0-9]+)$', cmms.views.service_preview, name='service_preview'),
    re_path(r'^podglad-licznika/(?P<mileage_id>[0-9]+)$', cmms.views.mileage_preview, name='mileage_preview'),
    re_path(r'^pobierz-dokument/(?P<document_id>[0-9]+)$',cmms.views.download_document, name='download_document'),
    path('ajax/mileage/<int:did>/', cmms.views.ajax_mileage, name='ajax_mileage'),
    re_path(r'^ajax/inspections/$', cmms.views.ajax_inspections, name='ajax_inspections'),
    re_path(r'^historia-serwisowa$', cmms.views.service_history, name='service_history'),
    re_path(r'^dokumenty-urzadzenia$', cmms.views.device_documents, name='device_documents'),
    re_path(r'^dokumenty-szkolenia$', cmms.views.device_instructions, name='device_instructions'),
    re_path(r'^urzadzenia-galeria$', cmms.views.device_gallery, name='device_gallery'),
    path('nowe-zlecenie', cmms.views.new_service, name='new_service'),
    path('nowy-licznik', cmms.views.new_mileage, name='new_mileage'),
    re_path(r'^manager-paszportow$', cmms.views.passport_manager, name="passport-manager"),
    re_path(r'^nowe-zgloszenie$', cmms.views.new_ticket),
    re_path(r'^pdf-preview/$', login_required(PDFPreview.as_view()), name='pdf-preview'),
    re_path(r'^pdf-generate/$', login_required(PDFGenerate.as_view()), name='pdf-generate'),
    re_path(r'^pdf-generate-directly/$', login_required(PDFGenerateDirectly.as_view()), name='pdf-generate-directly'),
    re_path(r'^pdf-generate-admin/(.*)$', utils.views.print_admin, name='pdf-generate-admin'),
    re_path(r'^xls-preview/$', login_required(GenerateXLSPreview.as_view()), name='xls-preview'),
    re_path(r'^xls-generate/$', login_required(GenerateXLS.as_view()), name='xls-generate'),
    #re_path(r'^qrcode-generate/$', cmms.views.generate_qrcodes, name='qrcode-generate'),
    re_path(r'^save_related_objects/$', utils.widget_filter_objects.save_related_objects, name='save_related_objects'),
    path('qrcode-generate/', generate_qrcodes, name='qrcode-generate'),
# comments
    path('add-comment', cmms.views.add_comment, name='add_comment'),
    path('comments/', include('django_comments.urls')),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

