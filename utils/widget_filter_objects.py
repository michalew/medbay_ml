# -*- coding: utf-8 -*-
from typing import Any
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from guardian.shortcuts import get_objects_for_user
from cmms.models import Device, Ticket, Service
from utils.datatables import generate_datatables_records, user_name_annotation

User = get_user_model()


@login_required
def get_filter_devices(request: HttpRequest) -> HttpResponse:
    return render(request, 'get_filter_devices.html')


@login_required
def get_filter_tickets(request: HttpRequest) -> HttpResponse:
    return render(request, 'get_filter_tickets.html')


@login_required
def get_filter_services(request: HttpRequest) -> HttpResponse:
    return render(request, 'get_filter_services.html')


@login_required
def get_filter_external_services(request: HttpRequest) -> HttpResponse:
    return render(request, 'get_filter_external_services.html')


@login_required
def ajax_filter_devices(request: HttpRequest) -> JsonResponse:
    querySet: QuerySet = get_objects_for_user(request.user, "cmms.view_device", accept_global_perms=False)

    exclude_ids_str = request.GET.get("exclude_id", "")
    if exclude_ids_str:
        exclude_ids = [int(id_) for id_ in exclude_ids_str.split(",") if id_]
        querySet = querySet.exclude(id__in=exclude_ids)

    querySet = querySet.annotate(
        person_responsible_n=user_name_annotation("person_responsible"),
        technical_supervisor_n=user_name_annotation("technical_supervisor")
    )

    columnIndexNameMap = {
        'lp': 'id',
        'person_responsible': 'person_responsible_n',
        'technical_supervisor': 'technical_supervisor_n'
    }

    return generate_datatables_records(request, querySet, columnIndexNameMap,
                                       'datatables/json_filter_devices.txt')


@login_required
def ajax_filter_tickets(request: HttpRequest) -> JsonResponse:
    querySet = Ticket.objects.all().annotate(
        person_creating_n=user_name_annotation("person_creating"),
        person_closing_n=user_name_annotation("person_closing")
    )

    columnIndexNameMap = {
        'lp': 'id',
        'person_creating': 'person_creating_n',
        'person_closing': 'person_closing_n'
    }

    return generate_datatables_records(request, querySet, columnIndexNameMap,
                                       'datatables/json_filter_tickets.txt')


@login_required
def ajax_filter_services(request: HttpRequest) -> JsonResponse:
    querySet = Service.objects.all().annotate(
        person_assigned_n=user_name_annotation("person_assigned"),
        person_creating_n=user_name_annotation("person_creating"),
        person_completing_n=user_name_annotation("person_completing")
    )

    columnIndexNameMap = {
        'lp': 'id',
        'person_assigned': 'person_assigned_n',
        'person_creating': 'person_creating_n',
        'person_completing': 'person_completing_n'
    }

    return generate_datatables_records(request, querySet, columnIndexNameMap,
                                       'datatables/json_filter_services.txt')


@login_required
def ajax_get_selected_devices(request: HttpRequest) -> JsonResponse:
    result: dict[int, dict[str, Any]] = {}
    ids_str = request.GET.get("ids", "")
    if ids_str:
        ids = [int(id_) for id_ in ids_str.split(",") if id_]
        querySet = Device.objects.filter(id__in=ids).order_by("-pk")
        for obj in querySet:
            result[obj.pk] = {
                "url": obj.get_absolute_url(),
                'name': str(obj),
                "make": str(obj.make) if obj.make else "",
                "model": obj.model,
                "serial_number": obj.serial_number,
                "inventory_number": obj.inventory_number,
                "location": str(obj.location) if obj.location else ""
            }
    return JsonResponse(result)


@login_required
def ajax_get_selected_services(request: HttpRequest) -> JsonResponse:
    result: dict[int, dict[str, Any]] = {}
    ids_str = request.GET.get("ids", "")
    if ids_str:
        ids = [int(id_) for id_ in ids_str.split(",") if id_]
        querySet = Service.objects.filter(id__in=ids).order_by("-pk")
        for obj in querySet:
            person_creating = "-"
            if obj.person_creating:
                person_creating = f"{obj.person_creating.first_name} {obj.person_creating.last_name}"

            person_completing = "-"
            if obj.person_completing:
                person_completing = f"{obj.person_completing.first_name} {obj.person_completing.last_name}"

            description_ticket = "".join(f"{ticket.description}</br>" for ticket in obj.ticket.all())

            result[obj.pk] = {
                "url": obj.get_absolute_url(),
                'name': str(obj),
                "timestamp": obj.timestamp.strftime("%d.%m.%Y"),
                "person_creating": person_creating,
                "contractor": str(obj.contractor) if obj.contractor else "",
                "status": obj.get_status_display(),
                "sort": obj.get_sort_display(),
                "description_ticket": description_ticket,
                "description": obj.description,
                "person_completing": person_completing
            }
    return JsonResponse(result)


@login_required
def ajax_get_selected_tickets(request: HttpRequest) -> JsonResponse:
    result: dict[int, dict[str, Any]] = {}
    ids_str = request.GET.get("ids", "")
    if ids_str:
        ids = [int(id_) for id_ in ids_str.split(",") if id_]
        querySet = Ticket.objects.filter(id__in=ids).order_by("-pk")
        for obj in querySet:
            person_creating = "-"
            if obj.person_creating:
                person_creating = f"{obj.person_creating.first_name} {obj.person_creating.last_name}"

            person_closing = "-"
            if obj.person_closing:
                person_closing = f"{obj.person_closing.first_name} {obj.person_closing.last_name}"

            result[obj.pk] = {
                "url": obj.get_absolute_url(),
                'name': str(obj),
                "timestamp": obj.timestamp.strftime("%d.%m.%Y") if obj.timestamp else "",
                "date_closing": obj.date_closing.strftime("%d.%m.%Y") if obj.date_closing else "",
                "sort": obj.get_sort_display(),
                "description": obj.description,
                "person_creating": person_creating,
                "status": obj.get_status_display(),
                "person_closing": person_closing,
            }
    return JsonResponse(result)


@login_required
def save_related_objects(request: HttpRequest) -> JsonResponse:
    result: dict = {}
    return JsonResponse(result)
