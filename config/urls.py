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
from django.urls import path, include
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
    MileageViewSet
)

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
]