import json
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext
from cmms.models import Make, Genre
from crm.models import Contractor, CostCentre
from dane.admin_forms import AdvancedServiceFilter, AdvancedDeviceFilter, AdvancedTicketFilter, AdvancedDocumentFilter, \
    AdvancedInvoiceFilter, AdvancedMileageFilter


def get_advanced_device_filter(request):
    context = {}
    context['advanced_filter_form'] = AdvancedDeviceFilter()
    return render(request, 'admin/dane/advanced_device_search.html', context)

def get_advanced_mileage_filter(request):
    context = {}
    context['advanced_filter_form'] = AdvancedMileageFilter()
    return render(request, 'admin/dane/advanced_mileage_search.html', context)

def get_advanced_service_filter(request):
    context = {}
    context['advanced_filter_form'] = AdvancedServiceFilter()
    return render(request, 'admin/dane/advanced_service_search.html', context)


def get_advanced_ticket_filter(request):
    context = {}
    context['advanced_filter_form'] = AdvancedTicketFilter()
    return render(request, 'admin/dane/advanced_ticket_search.html', context)


def get_advanced_invoice_filter(request):
    context = {}
    context['advanced_filter_form'] = AdvancedInvoiceFilter()
    return render(request, 'admin/dane/advanced_invoice_search.html', context)

def get_advanced_document_filter(request):
    context = {}
    context['advanced_filter_form'] = AdvancedDocumentFilter()
    return render(request, 'admin/dane/advanced_document_search.html', context)


def get_make(request):
    data = []
    term = request.GET.get("term")
    if term:
        makes = Make.objects.filter(name__icontains=term)
        data = [make.name for make in makes]
    data = list(set(data))

    return HttpResponse(json.dumps(data), content_type="application/json; charset=utf-8")


def get_genre(request):
    data = []
    term = request.GET.get("term")
    if term:
        genres = Genre.objects.filter(name__icontains=term)
        data = [genre.name for genre in genres]
    data = list(set(data))

    return HttpResponse(json.dumps(data), content_type="application/json; charset=utf-8")


def get_contractor(request):
    data = []
    term = request.GET.get("term")
    if term:
        contractors = Contractor.objects.filter(name__icontains=term)
        data = [contractor.name for contractor in contractors]

    data = list(set(data))

    return HttpResponse(json.dumps(data), content_type="application/json; charset=utf-8")


def get_contractor_change_form(request):
    data = []
    term = request.GET.get("term")
    if term:
        contractors = Contractor.objects.filter(name__icontains=term)
        data = [contractor.name for contractor in contractors]
        data = [{"value": contractor.pk, "label": contractor.name} for contractor in contractors]


    return HttpResponse(json.dumps(data), content_type="application/json; charset=utf-8")


def get_system_user(request):
    data = []
    term = request.GET.get("term")
    if term:
        users = get_user_model().objects.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))
        data = [{"value": user.pk, "label": u"%s %s" % (user.first_name, user.last_name)} for user in users]


    #data = list(set(data))

    return HttpResponse(json.dumps(data), content_type="application/json; charset=utf-8")


def get_cost_centre(request):
    data = []
    term = request.GET.get("term")
    if term:
        centre = CostCentre.objects.filter(name__icontains=term)
        data = [c.name for c in centre]
    data = list(set(data))

    return HttpResponse(json.dumps(data), content_type="application/json; charset=utf-8")

