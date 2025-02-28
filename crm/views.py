from django.views.generic import ListView
from django.http import JsonResponse
from .models import Hospital
from utils.gus_api import get_company_data


class HospitalListView(ListView):
    model = Hospital
    template_name = 'crm/hospitals.html'
    context_object_name = 'hospitals'

    def get_queryset(self):
        queryset = super().get_queryset()
        for obj in queryset:
            print(obj)  # Wyświetlanie instancji modelu w konsoli
        return queryset


def fetch_company_data(request):
    nip = request.GET.get('nip')
    if nip:
        company_data = get_company_data(nip)
        if company_data:
            return JsonResponse(company_data)
    return JsonResponse({'error': 'Invalid NIP or no data found'}, status=400)