from django.views.generic import ListView
from .models import Hospital


class HospitalListView(ListView):
    model = Hospital
    template_name = 'crm/hospitals.html'
    context_object_name = 'hospitals'

    def get_queryset(self):
        queryset = super().get_queryset()
        for obj in queryset:
            print(obj)  # Wyświetlanie instancji modelu w konsoli
        return queryset


