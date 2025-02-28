from django.urls import path

from . import views

app_name = 'crm'

urlpatterns = [
    path('hospitals', views.HospitalListView.as_view(), name='hospitals'),
    path('fetch-company-data/', views.fetch_company_data, name='fetch_company_data'),
]