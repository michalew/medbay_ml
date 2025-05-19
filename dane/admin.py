from django import forms
from django.contrib.auth import get_user_model
from django.urls import re_path
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django_comments.models import Comment
from django.forms.models import inlineformset_factory
from django.template.loader import render_to_string
from django.utils.html import mark_safe
from dane import admin_views
from cmms.models import *
from crm.cost_breakdown_creator import CostBreakdownCreator
from crm.cost_center_summary import CostCenterSummary
from crm.models import *
from django.contrib.auth.models import *
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
import urllib
import re
import csv
import datetime
from dateutil.relativedelta import relativedelta
from guardian.admin import GuardedModelAdmin

from django.contrib.admin import utils as admin_util
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse, Http404
from dane.admin_forms import AdvancedServiceFilter, AdvancedTicketFilter, AdvancedDeviceFilter, AdvancedDocumentFilter, TicketAdminForm, ServiceAdminForm, MileageAdminForm, DocumentAdminForm, \
    AdvancedInvoiceFilter, InvoiceAdminForm, InvoiceItemAdminForm, CostBreakdownForm, InvoiceItemFormSet, AdvancedMileageFilter, DevicePassportInlineForm
from reminders.forms import CalendarEventAdminForm
from reminders.models import CalendarEvent
from utils.views import render_xls, render_list_xls
from django_comments.models import Comment
from django.utils.html import escape
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from guardian.shortcuts import get_objects_for_user

from utils.tasks import setup_permissions
from django.contrib.auth.models import Permission

from dane.permission_filter import PermissionFilterMixin
from simple_history.admin import SimpleHistoryAdmin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse


User = get_user_model()

# TODO: remove this


class PermissionAdmin(admin.ModelAdmin):
    model = Permission

    def get_queryset(self, request):
        permissions = super(PermissionAdmin, self).get_queryset(request)

        # filter out some stuff
        permission_pks = [x.pk for x in Permission.objects.all() if x.content_type.natural_key()[
            0] == "cmms" or x.content_type.natural_key()[0] == "crm"]
        permissions = permissions.filter(pk__in=permission_pks)

        return permissions


class UnitAdmin(admin.ModelAdmin):
    model = Unit


class DevicePassportAdmin(admin.ModelAdmin):
    model = DevicePassport


def export_model_to_xls(modeladmin, request, queryset):
    """Export objects of modeladmin to *.xls file. Return response."""

    exported_columns = None
    if hasattr(modeladmin, 'exportable_fields'):
        exported_columns = modeladmin.exportable_fields
    response = render_xls(modeladmin.opts.model_name,
                          queryset, exported_columns)

    return response


export_model_to_xls.short_description = _('Export to XLS')


def open_print_form(modeladmin, request, queryset):
    """Opens print form for selected objects"""
    object_pks = ",".join([str(x.pk) for x in queryset])
    request.GET = request.GET.copy()
    request.GET['objects'] = object_pks
    model_name = modeladmin.model.__name__.lower()
    request.method = 'GET'

    from utils.views import print_admin
    return print_admin(request, model_name)


open_print_form.short_description = _("Wydruk")


def export_model_as_csv(modeladmin, request, queryset):
    if hasattr(modeladmin, 'exportable_fields'):
        field_list = modeladmin.exportable_fields
    else:
        # Copy modeladmin.list_display to remove action_checkbox
        field_list = modeladmin.list_display[:]
        field_list.remove('action_checkbox')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s-%s-export-%s.csv' % (
        __package__.lower(),
        queryset.model.__name__.lower(),
        datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'),
    )

    writer = csv.writer(response, encoding='windows-1250', delimiter=';')
    writer.writerow(
        [admin_util.label_for_field(f, queryset.model, modeladmin)
         for f in field_list],
    )

    for obj in queryset:
        csv_line_values = []
        for field in field_list:
            field_obj, attr, value = admin_util.lookup_field(
                field, obj, modeladmin)
            csv_line_values.append(value)

        writer.writerow(csv_line_values)

    return response


export_model_as_csv.short_description = _('Export to CSV')


def remove_from_fieldsets(fieldsets, fields):
    for fieldset in fieldsets:
        for field in fields:
            if field in fieldset[1]['fields']:
                new_fields = []
                for new_field in fieldset[1]['fields']:
                    if not new_field in fields:
                        new_fields.append(new_field)

                fieldset[1]['fields'] = tuple(new_fields)
                break


class DeviceGalleryInline(admin.TabularInline):
    model = DeviceGallery
    template = 'admin/edit_inline/tabular_device_images.html'
    verbose_name = u"Zdjęcie urządzenia"
    verbose_name_plural = u"Zdjęcia urządzenia"
    fields = ("image", "description", "is_visible")
    extra = 1
    #can_delete = False


class DevicePassportInline(admin.TabularInline):
    model = DevicePassport
    form = DevicePassportInlineForm
    template = 'admin/edit_inline/tabular_device_passport.html'
    verbose_name = u"Wpis do paszportu"
    verbose_name_plural = u"Wpisy do paszportu"
    extra = 1
    ordering = ("added_date", )
    fields = ("added_date", "content", )

    def has_add_permission(self, request):
        original_perm = super(DevicePassportInline,
                              self).has_add_permission(request)
        return request.user.has_perm('cmms.add_devicepassport') and original_perm


class DeviceAdmin(GuardedModelAdmin, SimpleHistoryAdmin):
    model = Device
#    prepopulated_fields = {'slug': ('title',)}

    def js_actions(self):
        return u""" <span class="nowrap"><a class="quick_edit_device" href="#%d">Podgląd</a> | <a class="quick_delete" href="#%d">Usuń</a></span> """ % (self.pk, self.pk)

    def device_get_group_name(self):
        return self.get_group_name()

    def device_get_status_name(self):
        return self.get_status_name()

    js_actions.short_description = u"Na skróty"
    device_get_group_name.short_description = u"grupa"
    device_get_status_name.short_description = u"status"
    js_actions.allow_tags = True

    list_display = ['id', 'name', 'make', 'model', 'serial_number',
                    'inventory_number', 'udt_number', 'genre', 'group',
                    'cost_centre', 'location', 'location_place',
                    'date_service', 'date_next_service', 'date_bought',
                    'date_manufactured', 'date_warranty', 'person_responsible',
                    'technical_supervisor', 'status', 'contractor', ]
    list_display_links = ['id', 'name', ]
    search_fields = ['name', 'genre__name', 'make__name', 'serial_number', 'inventory_number', 'model', 'udt_number',
                     'cost_centre__name', 'location__name', 'location__street', 'date_bought', 'date_manufactured',
                     'date_warranty', 'person_responsible__first_name', 'person_responsible__last_name',
                     'technical_supervisor__first_name', 'technical_supervisor__last_name', 'contractor__name']
    list_filter = ['genre', 'make', 'group', 'cost_centre', 'location',
                   'person_responsible', 'technical_supervisor', 'contractor', ]
    change_form_template = 'admin/guardian/model/change_form.html'
    change_list_template = 'admin/dane/change_list.html'
    actions = [export_model_to_xls, open_print_form]
    exportable_fields = ['id', 'name', 'make', 'model', 'serial_number', 
                         'inventory_number', 'udt_number', 'genre',
                         '_xls_get_group_name', 'cost_centre', 'location',
                         'date_service', 'date_next_service', 'date_bought',
                         'date_manufactured', 'date_warranty',
                         'person_responsible', 'technical_supervisor',
                         '_xls_get_status_name', 'contractor', ]
    readonly_fields = ["date_next_service", ]
    custom_filter_fields = []
    custom_combo_fields = ['make', 'genre', 'cost_centre', 'location',
                           'person_responsible', 'technical_supervisor', 'contractor']
    inlines = [DevicePassportInline, DeviceGalleryInline, ]
    excluded_inlines = ["DeviceGallery", ]
    ordering = ("-id",)

    fieldsets = (
        (
            u"Urządzenie", {
                "fields": (
                    'name',
                    'make',
                    'model',
                    'genre',
                    'group',
                    'status',
                ),
            }
        ), (
            u"Szczegóły urządzenia", {
                "fields": (
                    'serial_number',
                    'inventory_number',
                    'udt_number',
                    'date_manufactured',
                    'date_bought',
                    'date_warranty',
                ),
                'classes': ('collapse', 'open'),
            }
        ), (
            u"Lokalizacja i serwis", {
                "fields": (
                    'cost_centre',
                    'location',
                    'location_place',
                    'person_responsible',
                    'technical_supervisor',
                    'contractor',
                    'remarks',
                ),
                'classes': ('collapse', 'open'),
            }
        ), (
            u"Przegląd", {
                "fields": (
                    "date_service",
                    "service_interval",
                    "service_interval_type",
                    "date_next_service",
                ),
                'classes': ('collapse', 'open'),
            }
        ),
    )

    def save_formset(self, request, form, formset, change):
        deleted_images = [
            form.instance.pk for form in formset.deleted_forms if form.instance.pk]

        for form in formset:
            if not form.instance.pk in deleted_images:
                form.instance.added_user = request.user

        super(type(self), self).save_formset(request, form, formset, change)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_filter_fields'] = self.custom_filter_fields
        extra_context['object'] = self.get_object(request, object_id)
        extra_context['content_type_model'] = 'device'
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        extra_context['can_add_devicepassport'] = request.user.has_perm(
            "cmms.add_devicepassport")
        extra_context['can_update_devicepassport'] = request.user.has_perm(
            "cmms.update_devicepassport")

        return super(DeviceAdmin, self).change_view(request, object_id, form_url, extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = {}
        extra_context['content_type_model'] = 'device'
        extra_context['custom_combo_fields'] = self.custom_combo_fields

        return super(DeviceAdmin, self).add_view(request, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        if not request.user.has_perm('cmms.view_changelist_device'):
            raise PermissionDenied
        extra_context = {}
        extra_context['objects_name'] = [('device', u'Urządzenia')]
        extra_context['current_list_name'] = 'device'

        form = AdvancedDeviceFilter(request.POST.copy())
        last_filter_data = dict(form.data)
        last_filter = []
        for data in last_filter_data:
            key = "%s" % data
            last_filter.append({key: last_filter_data[data][0]})

        extra_context['last_data_filter'] = last_filter
        if request.method == "POST":
            extra_context['active_filter'] = True

        return super(DeviceAdmin, self).changelist_view(request, extra_context)

    def get_queryset(self, request):
        filters = {}
        excludes = {}
        user = request.user

        devices = get_objects_for_user(
            user, "cmms.view_device", accept_global_perms=False)

        if request.method == 'POST':
            request_data = request.POST.copy()
            form = AdvancedDeviceFilter(request_data)
            filter_data = dict(form.data)
            advanced_device_filter = form.data.get("advanced_device_filter")

            if advanced_device_filter:
                for data in filter_data:
                    if filter_data[data] and filter_data[data][0] != '':
                        if data == 'date_manufactured':
                            if filter_data['date_manufactured_operator'][0] == '1':
                                filters['date_manufactured'] = filter_data[data][0]
                            elif filter_data['date_manufactured_operator'][0] == '2':
                                filters['date_manufactured__gte'] = filter_data[data][0]
                            elif filter_data['date_manufactured_operator'][0] == '3':
                                filters['date_manufactured__lte'] = filter_data[data][0]
                            elif filter_data['date_manufactured_operator'][0] == '4':
                                filters['date_manufactured__gt'] = filter_data[data][0]
                            elif filter_data['date_manufactured_operator'][0] == '5':
                                filters['date_manufactured__lt'] = filter_data[data][0]
                        if data == 'date_manufactured_operator' and filter_data['date_manufactured_operator'][0] == '6':
                            if filter_data["date_manufactured_from"][0] != '' and \
                                    filter_data["date_manufactured_to"][0] != '':
                                filters['date_manufactured__gte'] = filter_data["date_manufactured_from"][0]
                                filters['date_manufactured__lt'] = filter_data["date_manufactured_to"][0]
                        if data == 'date_manufactured_operator' and filter_data['date_manufactured_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['date_manufactured__gte'] = now_minus_seven_days

                        if data == 'date_bought':
                            if filter_data['date_bought_operator'][0] == '1':
                                filters['date_bought'] = filter_data[data][0]
                            elif filter_data['date_bought_operator'][0] == '2':
                                filters['date_bought__gte'] = filter_data[data][0]
                            elif filter_data['date_bought_operator'][0] == '3':
                                filters['date_bought__lte'] = filter_data[data][0]
                            elif filter_data['date_bought_operator'][0] == '4':
                                filters['date_bought__gt'] = filter_data[data][0]
                            elif filter_data['date_bought_operator'][0] == '5':
                                filters['date_bought__lt'] = filter_data[data][0]
                        if data == 'date_bought_operator' and filter_data['date_bought_operator'][0] == '6':
                            if filter_data["date_bought_from"][0] != '' and filter_data["date_bought_to"][0] != '':
                                filters['date_bought__gte'] = filter_data["date_bought_from"][0]
                                filters['date_bought__lt'] = filter_data["date_bought_to"][0]
                        if data == 'date_bought_operator' and filter_data['date_bought_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['date_bought__gte'] = now_minus_seven_days

                        if data == 'date_warranty':
                            if filter_data['date_warranty_operator'][0] == '1':
                                filters['date_warranty'] = filter_data[data][0]
                            elif filter_data['date_warranty_operator'][0] == '2':
                                filters['date_warranty__gte'] = filter_data[data][0]
                            elif filter_data['date_warranty_operator'][0] == '3':
                                filters['date_warranty__lte'] = filter_data[data][0]
                            elif filter_data['date_warranty_operator'][0] == '4':
                                filters['date_warranty__gt'] = filter_data[data][0]
                            elif filter_data['date_warranty_operator'][0] == '5':
                                filters['date_warranty__lt'] = filter_data[data][0]
                        if data == 'date_warranty_operator' and filter_data['date_warranty_operator'][0] == '6':
                            if filter_data["date_warranty_from"][0] != '' and filter_data["date_warranty_to"][0] != '':
                                filters['date_warranty__gte'] = filter_data["date_warranty_from"][0]
                                filters['date_warranty__lt'] = filter_data["date_warranty_to"][0]
                        if data == 'date_warranty_operator' and filter_data['date_warranty_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['date_warranty__gte'] = now_minus_seven_days

                        if data == 'name':
                            if filter_data['name_operator'][0] == '1':
                                filters['name__icontains'] = filter_data[data][0]
                            elif filter_data['name_operator'][0] == '2':
                                excludes['name__icontains'] = filter_data[data][0]

                        if data == 'model':
                            if filter_data['model_operator'][0] == '1':
                                filters['model__icontains'] = filter_data[data][0]
                            elif filter_data['model_operator'][0] == '2':
                                excludes['model__icontains'] = filter_data[data][0]

                        if data == 'serial_number':
                            if filter_data['serial_number_operator'][0] == '1':
                                filters['serial_number__icontains'] = filter_data[data][0]
                            elif filter_data['serial_number_operator'][0] == '2':
                                excludes['serial_number__icontains'] = filter_data[data][0]

                        if data == 'inventory_number':
                            if filter_data['inventory_number_operator'][0] == '1':
                                filters['inventory_number__icontains'] = filter_data[data][0]
                            elif filter_data['inventory_number_operator'][0] == '2':
                                excludes['inventory_number__icontains'] = filter_data[data][0]

                        if data == 'udt_number':
                            if filter_data['udt_number_operator'][0] == '1':
                                filters['udt_number__icontains'] = filter_data[data][0]
                            elif filter_data['udt_number_operator'][0] == '2':
                                excludes['udt_number__icontains'] = filter_data[data][0]

                        if data == 'remarks':
                            if filter_data['remarks_operator'][0] == '1':
                                filters['remarks__icontains'] = filter_data[data][0]
                            elif filter_data['remarks_operator'][0] == '2':
                                excludes['remarks__icontains'] = filter_data[data][0]

                        if data == 'status':
                            if filter_data['status_operator'][0] == '1':
                                filters['status'] = filter_data[data][0]
                            elif filter_data['status_operator'][0] == '2':
                                excludes['status'] = filter_data[data][0]

                        if data == 'person_responsible':
                            if filter_data['person_responsible_operator'][0] == '1':
                                filters['person_responsible'] = filter_data[data][0]
                            elif filter_data['person_responsible_operator'][0] == '2':
                                excludes['person_responsible'] = filter_data[data][0]

                        if data == 'contractor':
                            if filter_data['contractor_operator'][0] == '1':
                                filters['contractor__name__icontains'] = filter_data[data][0]
                            elif filter_data['contractor_operator'][0] == '2':
                                excludes['contractor__name__icontains'] = filter_data[data][0]

                        if data == 'genre':
                            if filter_data['genre_operator'][0] == '1':
                                filters['genre__name__icontains'] = filter_data[data][0]
                            elif filter_data['genre_operator'][0] == '2':
                                excludes['genre__name__icontains'] = filter_data[data][0]

                        if data == 'make':
                            if filter_data['make_operator'][0] == '1':
                                filters['make__name__icontains'] = filter_data[data][0]
                            elif filter_data['make_operator'][0] == '2':
                                excludes['make__name__icontains'] = filter_data[data][0]

                        if data == 'group':
                            if filter_data['group_operator'][0] == '1':
                                filters['group'] = filter_data[data][0]
                            elif filter_data['group_operator'][0] == '2':
                                excludes['group'] = filter_data[data][0]

                        if data == 'cost_centre':
                            if filter_data['cost_centre_operator'][0] == '1':
                                filters['cost_centre__name__icontains'] = filter_data[data][0]
                            elif filter_data['cost_centre_operator'][0] == '2':
                                excludes['cost_centre__name__icontains'] = filter_data[data][0]

                        if data == 'location':
                            if filter_data['location_operator'][0] == '1':
                                filters['location'] = filter_data[data][0]
                            elif filter_data['location_operator'][0] == '2':
                                excludes['location'] = filter_data[data][0]

                        if data == 'location_place':
                            if filter_data['location_place_operator'][0] == '1':
                                filters['location_place__icontains'] = filter_data[data][0]
                            elif filter_data['location_place_operator'][0] == '2':
                                excludes['location_place__icontains'] = filter_data[data][0]

                        if data == 'technical_supervisor':
                            if filter_data['technical_supervisor_operator'][0] == '1':
                                filters['technical_supervisor'] = filter_data[data][0]
                            elif filter_data['technical_supervisor_operator'][0] == '2':
                                excludes['technical_supervisor'] = filter_data[data][0]

            devices = devices.filter(**filters).exclude(**excludes)
        return devices

    def get_urls(self):
        urls = super(DeviceAdmin, self).get_urls()

        my_urls = [
            re_path(r'^get_advanced_device_filter/$', admin_views.get_advanced_device_filter, name='get_advanced_device_filter'),
            re_path(r'^get_make/$', admin_views.get_make, name='get_make'),
            re_path(r'^get_genre/$', admin_views.get_genre, name='get_genre'),
            re_path(r'^get_contractor/$', admin_views.get_contractor, name='get_contractor'),
            re_path(r'^get_cost_centre/$', admin_views.get_cost_centre, name='get_cost_centre'),
        ]
        return my_urls + urls


class GenreAdmin(SimpleHistoryAdmin):
    model = Genre

    list_display = ['name', 'symbol', ]
    search_fields = ['name', 'symbol', ]
    change_form_template = 'admin/dane/change_form.html'
    change_list_template = 'admin/dane/change_list.html'


class DocumentTicketInline(admin.TabularInline):
    model = Document.ticket.through
    verbose_name = u"Załącznik lub dokument"
    verbose_name_plural = u"Załączniki i dokumenty"
    template = 'admin/edit_inline/tabular_document_ticket.html'

    def has_add_permission(self, request):
        original_perm = super(DocumentTicketInline,
                              self).has_add_permission(request)
        return request.user.has_perm('cmms.add_document_ticket') and original_perm


class TicketAdmin(GuardedModelAdmin, SimpleHistoryAdmin):
    model = Ticket
    form = TicketAdminForm
    ordering = ("-id",)

    def js_actions(self):
        return u""" <span class="nowrap"><a class="quick_edit_ticket" href="#%d">Podgląd</a> | <a class="quick_delete" href="#%d">Usuń</a></span> """ % (self.pk, self.pk)
    js_actions.short_description = u"Na skróty"
    js_actions.allow_tags = True

    def get_devices(self):
        devices = self.get_devices()
        arr = []
        for d in devices:
            arr.append("<nobr>%s: <a href=\"/a/cmms/device/%s\">%s</a></nobr>" %
                       (d.inventory_number, d.pk, d.name))
        return "<br>".join(arr)
    get_devices.short_description = u"Urządzenia"
    get_devices.allow_tags = True

    def get_locations(self):
        devices = self.device.all()
        arr = []
        for d in devices:
            arr.append("<nobr>%s, %s</nobr>" % (d.cost_centre, d.location))
        return "<br>".join(arr)
    get_locations.short_description = u"Centrum kosztowe, lokalizacja"
    get_locations.allow_tags = True

    list_display = ['id', 'sort', 'priority', get_devices, get_locations, 'description', 'status',
                    'created_ticket_date', 'timestamp', 'person_creating_name', 'date_closing', 'person_closing_name', 'cost', ]
    list_display_links = ['id', 'sort', ]
    search_fields = ['device__name', 'device__genre__name', 'device__make__name', 'device__model', 'timestamp', 'description', 'status',
                     'person_creating__first_name', 'person_creating__last_name', 'person_closing__first_name', 'person_closing__last_name', ]
    list_filter = ['sort', 'status', 'person_creating', 'device', ]
    change_form_template = 'admin/guardian/model/change_form.html'
    change_list_template = 'admin/dane/change_list.html'
    filter_horizontal = ('device', )
    actions = [export_model_to_xls, open_print_form]

    exportable_fields = list_display[:]  # copy list using slice
    exportable_fields[3] = '_xls_get_devices'
    exportable_fields[4] = '_xls_get_locations'
    custom_filter_fields = ('device',)
    custom_combo_fields = ['person_creating', 'contractor', 'person_completing',
                           'person_execute', 'contractor_execute', 'person_closing']

    fieldsets = (
        (u"Zgłoszone urządzenia", {
         "fields": ('device',), 'classes': ('collapse', 'open'), }),
        (u"Szczegóły zgłoszenia", {"fields": (
            'sort',
            'priority',
            'cyclic',
            'description',
            'status',
            'timestamp',
            'person_creating',
            "planned_date_execute",
            "contractor",
            "person_completing",
            "date_execute",
            "person_execute",
            "contractor_execute",
            'date_closing',
            'person_closing',
        ), }),
        (u"Podsumowanie", {"fields": ('summation',), }),
    )

    inlines = [DocumentTicketInline, ]

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(TicketAdmin, self).get_fieldsets(request, obj)

        # reset fields
        self.readonly_fields = ()

        if not request.user.has_perm('cmms.change_devices_ticket'):
            self.readonly_fields += ('device',)

        if not request.user.has_perm('cmms.change_summation_ticket'):
            self.readonly_fields += ('summation',)

        if not request.user.has_perm('cmms.change_description_ticket'):
            self.readonly_fields += ('description',)

        if not request.user.has_perm('cmms.change_details_ticket'):
            self.readonly_fields += ('sort', 'priority', 'cyclic', 'status', 'timestamp', 'person_creating',
                                     "planned_date_execute", "contractor", "person_completing", "date_execute", "person_execute",
                                     "contractor_execute", 'date_closing', 'person_closing',)
        return fieldsets

    def get_printed_fieldsets(self, request, obj=None):
        return [
            (u'Zg\u0142oszone urz\u0105dzenia', [
                ('device', u'Urz\u0105dzenie')
            ]),
            (u'Szczeg\xf3\u0142y zg\u0142oszenia', [
                ('sort', u'Rodzaj zg\u0142oszenia'),
                ('priority', u'Priorytet'),
                ('cyclic', u'Cykliczny?'),
                ('description', u'Opis'),
                ('status', u'Status'),
                ('timestamp', u'Data rozpocz\u0119cia'),
                ('person_creating', u'Zg\u0142aszaj\u0105cy'),
                ('planned_date_execute', u'Planowana data wykonania'),
                ('contractor', u'Firma serwisuj\u0105ca'),
                ('person_completing', u'Odbiorca zlecenia'),
                ('date_execute', u'Data wykonania'),
                ('person_execute', u'Osoba wykonuj\u0105ca'),
                ('contractor_execute', u'Firma wykonuj\u0105ca'),
                ('date_closing', u'Data zamkni\u0119cia'),
                ('person_closing', u'Osoba zamykaj\u0105ca')
            ]),
            (u'Podsumowanie', [
                ('summation', u'Podsumowanie')
            ]),
            (u'Za\u0142\u0105cznik lub dokument', [
                ('inline_Document_ticket', u'Za\u0142\u0105cznik lub dokument')
            ]),
            ('Komentarze', [
                ('comments', 'Komentarze')
            ])
        ]

    def get_default_selected(self, request, obj=None):
        return ['device', 'sort', 'priority', 'status', 'timestamp', 'person_creating', 'summation',
                'inline_Document_ticket', 'comments']

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_filter_fields'] = self.custom_filter_fields
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        extra_context['object'] = self.get_object(request, None)
        extra_context['can_add_comment'] = False
        extra_context['content_type_model'] = 'ticket'

        return super(TicketAdmin, self).add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = {}
        if request.user.has_perm('cmms.change_devices_ticket'):
            extra_context['custom_filter_fields'] = self.custom_filter_fields
        else:
            extra_context['custom_filter_fields'] = ()

        extra_context['custom_combo_fields'] = self.custom_combo_fields
        obj = self.get_object(request, object_id)
        extra_context['object'] = obj
        extra_context['content_type_model'] = 'ticket'

        if obj:
            extra_context['can_add_comment'] = obj.status != 2 or request.user.is_superuser
        else:
            extra_context['can_add_comment'] = False

        return super(TicketAdmin, self).change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        if not request.user.has_perm('cmms.view_changelist_ticket'):
            raise PermissionDenied
        extra_context = {}
        extra_context['objects_name'] = [
            ('device', u'Urządzenia'), ('ticket', u'Zgłoszenia')]
        extra_context['current_list_name'] = 'ticket'

        form = AdvancedTicketFilter(request.POST.copy())
        last_filter_data = dict(form.data)
        last_filter = []
        for data in last_filter_data:
            key = "%s" % data
            last_filter.append({key: last_filter_data[data][0]})

        extra_context['last_data_filter'] = last_filter
        if request.method == "POST":
            extra_context['active_filter'] = True

        return super(TicketAdmin, self).changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        super(TicketAdmin, self).save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """
        TODO: zrobić to po ludzku

        oryginalnie było tu instances = form.save(commit=False), jednak linijka ta wywala się to przy usuwaniu obiektów (#173)
        pobranie queryseta i porównanie z obiektami obecnie zapisanymi nie zmieni nic, bo oba są identyczne

        żeby wyłapać nowe obiekty, obchodzę to przechodząc przez wszystkie wpisy w formularzu i wyłapując ID obiektów
        nawet działa
        """
        object_id = request.META['PATH_INFO'].strip(
            '/').split('/')[-1]  # get ticket ID
        data = formset.data
        # all documents from queryset
        query = [x.document for x in formset.queryset]

        # initialize variable
        new_objects = ()

        for obj in data.keys():
            if obj.startswith("Document_ticket-") and obj.endswith("-document"):
                if data[obj] != "":
                    document = Document.objects.get(pk=data[obj])
                    new_objects += (document,)

        # get all new objects
        instances = [x for x in new_objects if x not in query]

        for i in instances:
            comment = u"Osoba dokonująca zmian: %s<br/><br/>Wprowadzone zmiany:<br/>" % (
                request.user)
            comment += u"""Dodano dokument/załącznik: %s: %s<br />
                    <a target=\"_blank\" href=\"%s\">Skan</a>&nbsp;|&nbsp;
                    <a target=\"_blank\" href=\"/a/cmms/document/%s/\">Edycja</a>
                    """ % (
                i.get_sort_name(), 
                i.name, 
                reverse('download_document', args=(i.pk, )), 
                i.pk
            )
            now = datetime.datetime.now()
            Comment.objects.create(comment=comment, site_id=1, object_pk=object_id,
                                   content_type_id=34, user_id=request.user.pk, submit_date=now)

        super(type(self), self).save_formset(request, form, formset, change)

    def get_queryset(self, request):
        filters = {}
        excludes = {}

        user = request.user

        tickets = super(TicketAdmin, self).get_queryset(request)
        devices = get_objects_for_user(
            user, "cmms.view_device", accept_global_perms=False)

        users = [request.user.pk, ]
        all_users = UserProfile.objects.all()  # get all users
        if request.user.is_superuser:
            users = [x.pk for x in all_users]
        else:
            # get all locations person is responsible for
            locations = request.user.person.all()
            for location in locations:
                users += [x.pk for x in location.staff.all()]

            for user in all_users:
                if user.pk in users:
                    continue
                # nadzor techniczny
                if request.user.has_perm("cmms.view_all_devices"):
                    users += [user.pk, ]

        tickets = tickets.filter(Q(device__in=devices) |
                                 Q(person_creating__in=users) |
                                 Q(person_creating__isnull=True)).distinct()

        if request.method == 'POST':
            request_data = request.POST.copy()
            form = AdvancedTicketFilter(request_data)
            filter_data = dict(form.data)
            advanced_ticket_filter = form.data.get("advanced_ticket_filter")

            if advanced_ticket_filter:
                for data in filter_data:
                    if filter_data[data] and filter_data[data][0] != '':
                        if data == 'device':
                            if filter_data['device_operator'][0] == '1':
                                filters['device__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]
                            elif filter_data['device_operator'][0] == '2':
                                excludes['device__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]

                        if data == 'date_add':
                            if filter_data['date_add_operator'][0] == '1':
                                filters['timestamp'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '2':
                                filters['timestamp__gte'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '3':
                                filters['timestamp__lte'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '4':
                                filters['timestamp__gt'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '5':
                                filters['timestamp__lt'] = filter_data[data][0]
                        if data == 'date_add_operator' and filter_data['date_add_operator'][0] == '6':
                            if filter_data["date_add_from"][0] != '' and filter_data["date_add_to"][0] != '':
                                filters['timestamp__gte'] = filter_data["date_add_from"][0]
                                filters['timestamp__lt'] = filter_data["date_add_to"][0]
                        if data == 'date_add_operator' and filter_data['date_add_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['timestamp__gte'] = now_minus_seven_days

                        if data == 'date_closing':
                            if filter_data['date_closing_operator'][0] == '1':
                                filters['date_closing'] = filter_data[data][0]
                            elif filter_data['date_closing_operator'][0] == '2':
                                filters['date_closing__gte'] = filter_data[data][0]
                            elif filter_data['date_closing_operator'][0] == '3':
                                filters['date_closing__lte'] = filter_data[data][0]
                            elif filter_data['date_closing_operator'][0] == '4':
                                filters['date_closing__gt'] = filter_data[data][0]
                            elif filter_data['date_closing_operator'][0] == '5':
                                filters['date_closing__lt'] = filter_data[data][0]
                        if data == 'date_closing_operator' and filter_data['date_closing_operator'][0] == '6':
                            if filter_data["date_closing_from"][0] != '' and filter_data["date_closing_to"][0] != '':
                                filters['date_closing__gte'] = filter_data["date_closing_from"][0]
                                filters['date_closing__lt'] = filter_data["date_closing_to"][0]
                        if data == 'date_closing_operator' and filter_data['date_closing_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['date_closing__gte'] = now_minus_seven_days

                        if data == 'sort':
                            if filter_data['sort_operator'][0] == '1':
                                filters['sort'] = filter_data[data][0]
                            elif filter_data['sort_operator'][0] == '2':
                                excludes['sort'] = filter_data[data][0]

                        if data == 'description':
                            if filter_data['description_operator'][0] == '1':
                                filters['description__icontains'] = filter_data[data][0]
                            elif filter_data['description_operator'][0] == '2':
                                excludes['description__icontains'] = filter_data[data][0]

                        if data == 'status':
                            if filter_data['status_operator'][0] == '1':
                                filters['status'] = filter_data[data][0]
                            elif filter_data['status_operator'][0] == '2':
                                excludes['status'] = filter_data[data][0]

                        if data == 'priority':
                            if filter_data['priority_operator'][0] == '1':
                                filters['priority'] = filter_data[data][0]
                            elif filter_data['priority_operator'][0] == '2':
                                excludes['priority'] = filter_data[data][0]

                        if data == 'person_creating':
                            if filter_data['person_creating_operator'][0] == '1':
                                filters['person_creating'] = filter_data[data][0]
                            elif filter_data['person_creating_operator'][0] == '2':
                                excludes['person_creating'] = filter_data[data][0]

                        if data == 'person_closing':
                            if filter_data['person_closing_operator'][0] == '1':
                                filters['person_closing'] = filter_data[data][0]
                            elif filter_data['person_closing_operator'][0] == '2':
                                excludes['person_closing'] = filter_data[data][0]

                        if data == 'cyclic':
                            if filter_data['cyclic_operator'][0] == '1':
                                filters['cyclic'] = filter_data[data][0]
                            elif filter_data['cyclic_operator'][0] == '2':
                                excludes['cyclic'] = filter_data[data][0]

                        if data == 'comment':
                            content_type = ContentType.objects.filter(model='ticket')[
                                :1]
                            if content_type:
                                content_type_id = content_type[0].pk
                                service_pks = Comment.objects.filter(
                                    comment__icontains=filter_data[data][0], content_type=content_type_id
                                ).values_list("object_pk", flat=True)
                                ids = [int(pk) for pk in service_pks]
                                if filter_data['comment_operator'][0] == '1':
                                    filters['pk__in'] = ids
                                elif filter_data['comment_operator'][0] == '2':
                                    excludes['pk__in'] = ids

            tickets = tickets.filter(**filters).exclude(**excludes)
        return tickets

    def get_urls(self):
        urls = super(TicketAdmin, self).get_urls()

        my_urls = [
            re_path(r'^get_advanced_ticket_filter/$', 'dane.admin_views.get_advanced_ticket_filter',
                name='get_advanced_ticket_filter'),
            re_path(r'^/get_contractor/$', 'dane.admin_views.get_contractor',
                name='get_contractor'),
        ]
        return my_urls + urls

    def get_form(self, request, obj=None):
        form = super(TicketAdmin, self).get_form(request, obj)
        form.current_user = request.user
        return form


class DocumentServiceInline(admin.TabularInline):
    model = Document.service.through
    verbose_name = u"Załącznik lub dokument"
    verbose_name_plural = u"Załączniki i dokumenty"
    template = 'admin/edit_inline/tabular_document_ticket.html'

    def has_add_permission(self, request):
        original_perm = super(DocumentServiceInline,
                              self).has_add_permission(request)
        return request.user.has_perm('cmms.add_document_service') and original_perm


class ServiceAdmin(GuardedModelAdmin, SimpleHistoryAdmin):
    model = Service
    form = ServiceAdminForm

    def service_get_sort_name(self):
        return self.get_sort_name()

    def service_get_status_name(self):
        return self.get_status_name()

    def get_ticket_date(self):
        return self.ticket.timestamp()

    filter_horizontal = ('ticket', )
    service_get_sort_name.short_description = u"Rodzaj zlecenia"
    service_get_status_name.short_description = u"Status"
    list_display = ['id', 'contractor', 'person_completing', 'timestamp',
                    'sort', 'person_assigned', 'description', 'status', 'person_creating', ]
    list_display_links = ['id', 'contractor', ]
    search_fields = ['ticket__device__name', 'ticket__device__genre__name', 'ticket__device__make__name', 'ticket__device__model', 'timestamp', 'person_assigned__first_name',
                     'person_assigned__last_name', 'description', 'person_creating__first_name', 'person_creating__last_name', 'contractor__name', 'person_completing__first_name', 'person_completing__last_name', ]
    list_filter = ['sort', 'status', 'person_creating',
                   'person_assigned',  'contractor', 'person_completing', ]
    change_form_template = 'admin/guardian/model/change_form.html'
    #change_form_template = 'admin/dane/change_form.html'
    change_list_template = 'admin/dane/change_list.html'
    actions = [export_model_to_xls, open_print_form]
    ordering = ("-id",)
    exportable_fields = ['contractor', 'person_completing', 'timestamp', service_get_sort_name,
                         'person_assigned', 'description', service_get_status_name, 'person_creating', ]
    exportable_fields[3] = '_xls_get_sort_name'
    exportable_fields[6] = '_xls_get_status_name'
    exportable_fields.insert(0, 'id')
    custom_filter_fields = ('ticket',)
    custom_combo_fields = ['person_creating', 'person_assigned',
                           'contractor', 'person_completing', 'hospital']
    fieldsets = (
        (u"Zgłoszenie", {"fields": ('ticket', ),
                         'classes': ('collapse', 'open',), }),
        (u"Dane zlecenia", {"fields": (
            # 'timestamp',
            'sort',
            'person_creating',
            'person_assigned',
            "contractor",
            "person_completing",
            'description',
            'status',
            'hospital',
        ), }),
        (u"Podsumowanie", {"fields": ('summation',), }),
    )

    inlines = [DocumentServiceInline, ]

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(ServiceAdmin, self).get_fieldsets(request, obj)

        # reset readonly fields
        self.readonly_fields = ("person_creating", )

        if not request.user.has_perm('cmms.change_tickets_service'):
            self.readonly_fields += ('ticket',)

        if not request.user.has_perm('cmms.change_summation_service'):
            self.readonly_fields += ('summation',)

        if not request.user.has_perm('cmms.change_data_service'):
            self.readonly_fields += ('sort', 'person_creating', 'person_assigned', "contractor",
                                     "person_completing", 'description', 'status', 'hospital',)        
        return fieldsets

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_filter_fields'] = self.custom_filter_fields
        extra_context['object'] = self.get_object(request, None)
        extra_context['custom_combo_fields'] = self.custom_combo_fields

        extra_context['can_add_comment'] = False

        extra_context['content_type_model'] = 'service'
        return super(ServiceAdmin, self).add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_filter_fields'] = self.custom_filter_fields
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        obj = self.get_object(request, object_id)
        extra_context['object'] = obj
        extra_context['content_type_model'] = 'service'

        try:
            extra_context['can_add_comment'] = obj.status != 5 or request.user.is_superuser
        except:
            extra_context['can_add_comment'] = False

        return super(ServiceAdmin, self).change_view(request, object_id, form_url, extra_context)

    def save_formset(self, request, form, formset, change):
        # TODO: zrobić to po ludzku, to samo co przy TicketAdmin
        object_id = request.META['PATH_INFO'].strip(
            '/').split('/')[-1]  # get service ID
        data = formset.data
        # all documents from queryset
        query = [x.document for x in formset.queryset]

        # initialize variable
        new_objects = ()

        for obj in data.keys():
            if obj.startswith("Document_service-") and obj.endswith("-document"):
                if data[obj] != "":
                    document = Document.objects.get(pk=data[obj])
                    new_objects += (document,)

        # get all new objects
        instances = [x for x in new_objects if x not in query]

        for i in instances:
            comment = u"Osoba dokonująca zmian: %s<br/><br/>Wprowadzone zmiany:<br/>" % (
                request.user)
            comment += u"""Dodano dokument/załącznik: %s: %s<br />
                <a target=\"_blank\" href=\"%s\">Skan</a>&nbsp;|&nbsp;
                <a target=\"_blank\" href=\"/a/cmms/document/%s/\">Edycja</a>
            """ % (
                i.get_sort_name(), 
                i.name, 
                reverse('download_document', args=(i.pk, )), 
                i.pk
            )
            now = datetime.datetime.now()
            Comment.objects.create(comment=comment, site_id=1, object_pk=object_id, content_type_id=35,
                                   user_id=request.user.pk, submit_date=now)
        super(type(self), self).save_formset(request, form, formset, change)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.person_creating = request.user

        super(ServiceAdmin, self).save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        if not request.user.has_perm('cmms.view_changelist_service'):
            raise PermissionDenied
        extra_context = {}
        extra_context['objects_name'] = [
            ('service', 'Zlecenia'), ('ticket', u'Zgłoszenia')]
        extra_context['current_list_name'] = 'service'

        form = AdvancedServiceFilter(request.POST.copy())
        last_filter_data = dict(form.data)
        last_filter = []
        for data in last_filter_data:
            key = "%s" % data
            last_filter.append({key: last_filter_data[data][0]})

        extra_context['last_data_filter'] = last_filter
        if request.method == "POST":
            extra_context['active_filter'] = True

        return super(ServiceAdmin, self).changelist_view(request, extra_context)

    def get_queryset(self, request):
        filters = {}
        excludes = {}
        user = request.user

        services = super(ServiceAdmin, self).get_queryset(request)
        devices = get_objects_for_user(
            user, "cmms.view_device", accept_global_perms=False)
        tickets = Ticket.objects.filter(device__in=devices)
        services = services.filter(ticket__in=tickets).distinct()

        if request.method == 'POST':
            request_data = request.POST.copy()
            form = AdvancedServiceFilter(request_data)
            filter_data = dict(form.data)
            advanced_service_filter = form.data.get("advanced_service_filter")

            if advanced_service_filter:
                for data in filter_data:
                    if filter_data[data] and filter_data[data][0] != '':
                        if data == 'ticket':
                            if filter_data['ticket_operator'][0] == '1':
                                filters['ticket__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]
                            elif filter_data['ticket_operator'][0] == '2':
                                excludes['ticket__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]

                        if data == 'hospital':
                            if filter_data['hospital_operator'][0] == '1':
                                filters['hospital'] = filter_data[data][0]
                            elif filter_data['hospital_operator'][0] == '2':
                                excludes['hospital'] = filter_data[data][0]

                        if data == 'sort':
                            if filter_data['sort_operator'][0] == '1':
                                filters['sort'] = filter_data[data][0]
                            elif filter_data['sort_operator'][0] == '2':
                                excludes['sort'] = filter_data[data][0]

                        if data == 'person_assigned':
                            if filter_data['person_assigned_operator'][0] == '1':
                                filters['person_assigned'] = filter_data[data][0]
                            elif filter_data['person_assigned_operator'][0] == '2':
                                excludes['person_assigned'] = filter_data[data][0]

                        if data == 'description':
                            if filter_data['description_operator'][0] == '1':
                                filters['description__icontains'] = filter_data[data][0]
                            elif filter_data['description_operator'][0] == '2':
                                excludes['description__icontains'] = filter_data[data][0]

                        if data == 'status':
                            if filter_data['status_operator'][0] == '1':
                                filters['status'] = filter_data[data][0]
                            elif filter_data['status_operator'][0] == '2':
                                excludes['status'] = filter_data[data][0]

                        if data == 'person_creating':
                            if filter_data['person_creating_operator'][0] == '1':
                                filters['person_creating'] = filter_data[data][0]
                            elif filter_data['person_creating_operator'][0] == '2':
                                excludes['person_creating'] = filter_data[data][0]

                        if data == 'contractor':
                            if filter_data['contractor_operator'][0] == '1':
                                filters['contractor__name__icontains'] = filter_data[data][0]
                            elif filter_data['contractor_operator'][0] == '2':
                                excludes['contractor__name__icontains'] = filter_data[data][0]

                        if data == 'person_completing':
                            if filter_data['person_completing_operator'][0] == '1':
                                filters['person_completing'] = filter_data[data][0]
                            elif filter_data['person_completing_operator'][0] == '2':
                                excludes['person_completing'] = filter_data[data][0]

                        if data == 'date_add':
                            if filter_data['date_add_operator'][0] == '1':
                                filters['timestamp'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '2':
                                filters['timestamp__gte'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '3':
                                filters['timestamp__lte'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '4':
                                filters['timestamp__gt'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '5':
                                filters['timestamp__lt'] = filter_data[data][0]
                        if data == 'date_add_operator' and filter_data['date_add_operator'][0] == '6':
                            if filter_data["date_add_from"][0] != '' and filter_data["date_add_to"][0] != '':
                                filters['timestamp__gte'] = filter_data["date_add_from"][0]
                                filters['timestamp__lt'] = filter_data["date_add_to"][0]
                        if data == 'date_add_operator' and filter_data['date_add_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['timestamp__gte'] = now_minus_seven_days

                        if data == 'comment':
                            content_type = ContentType.objects.filter(model='service')[
                                :1]
                            if content_type:
                                content_type_id = content_type[0].pk
                                service_pks = Comment.objects.filter(
                                    comment__icontains=filter_data[data][0], content_type=content_type_id
                                ).values_list("object_pk", flat=True)
                                ids = [int(pk) for pk in service_pks]
                                if filter_data['comment_operator'][0] == '1':
                                    filters['pk__in'] = ids
                                elif filter_data['comment_operator'][0] == '2':
                                    excludes['pk__in'] = ids

            services = services.filter(**filters).exclude(**excludes)

        return services

    def get_urls(self):

        urls = super(ServiceAdmin, self).get_urls()

        my_urls = [
re_path(r'^get_advanced_service_filter/$', 'dane.admin_views.get_advanced_service_filter',
                name='get_advanced_service_filter'),
            re_path(r'^get_contractor/$', 'dane.admin_views.get_contractor',
                name='get_contractor'),
        
]
        return my_urls + urls

    def get_form(self, request, obj=None):
        form = super(ServiceAdmin, self).get_form(request, obj)
        form.current_user = request.user
        return form


class MakeAdmin(SimpleHistoryAdmin):
    model = Make
    list_display = ['name', ]
    search_fields = ['name', ]
    change_form_template = 'admin/dane/change_form.html'
    change_list_template = 'admin/dane/change_list.html'


class ContractorAdmin(SimpleHistoryAdmin):
    model = Contractor
    list_display = ['name', 'NIP', 'email', 'city', ]
    search_fields = ['name', 'NIP', 'email', 'city', ]
    ordering = ("-id",)
    change_form_template = 'admin/dane/change_form.html'
    change_list_template = 'admin/dane/change_list.html'

    filter_horizontal = ('staff', )

    """
    name = models.CharField(max_length=255, verbose_name=u'Nazwa')
    NIP = models.BigIntegerField(verbose_name=u'NIP')
    street = models.CharField(max_length=255, verbose_name=u'Ulica')
    street_number = models.CharField(max_length=255, verbose_name=u'Nr posesji')
    postal_code = models.CharField(max_length=255, verbose_name=u'Kod pocztowy')
    city = models.CharField(max_length=255, verbose_name=u'Miejscowość')
    email = models.EmailField(blank=True, null=True)
    staff = models.ManyToManyField(User, verbose_name=u'Pracownicy', related_name='contractor_staff', blank=True)
    """

    def get_fieldsets(self, request, obj=None):
        fieldsets = (
            (None, {
                'fields': (
                    'name',
                    'NIP',
                    'street',
                    'street_number',
                    'postal_code',
                    'city',
                    'email',
                )
            }),
        )

        if obj:
            fieldsets += (u"Pracownicy", {
                "fields": ('staff',),
            }),
        else:
            fieldsets += (u"Pracownicy", {
                "fields": ('staff',), 'classes': ('collapse', 'closed'),
            }),

        return fieldsets

    def __get_object(self, request):
        object_id = request.META['PATH_INFO'].strip('/').split('/')[-1]
        try:
            object_id = int(object_id)
        except ValueError:
            return None
        return self.model.objects.get(pk=object_id)

    def save_related(self, request, form, formsets, change):
        try:
            contractor = self.__get_object(request)
            users = UserProfile.objects.filter(contractor_staff=contractor)

            # check if permissions have changed
            staff_changed = contractor.staff.all(
            ) != form.cleaned_data['staff']
        except:
            staff_changed = False
            pass

        super(ContractorAdmin, self).save_related(
            request, form, formsets, change)

        # TOOD: check if device permissions changed before changing anything
        # update permissions
        if staff_changed:
            for user in users:
                view_all_devices = user.has_perm("cmms.view_all_devices")

                # update permissions for devices
                if view_all_devices:
                    user_devices = Device.objects.all()
                else:
                    user_devices = Device.objects.filter(contractor=contractor)

                # get list of devices to reset
                reset_devices = get_objects_for_user(
                    user, 'cmms.view_device', accept_global_perms=False) | user_devices

                # push task
                setup_permissions.delay(user.pk, [i.pk for i in reset_devices], [
                                        i.pk for i in user_devices])


class CostCentreAdmin(admin.ModelAdmin):
    model = CostCentre
    list_display = ['name', 'symbol', 'description', ]
    search_fields = ['name', 'symbol', 'description', ]
    change_form_template = 'admin/dane/change_form.html'
    change_list_template = 'admin/dane/change_list.html'
    ordering = ("-id",)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    form = InvoiceItemAdminForm
    formset = InvoiceItemFormSet


class CostBreakdownInline(admin.TabularInline):
    model = CostBreakdown
    form = CostBreakdownForm
    exclude = ['cost_center_name',
               'cost_center_description', 'cost_center_symbol']
    max_num = 0
    extra = 0


class InvoiceAdmin(admin.ModelAdmin):
    inlines = [
        InvoiceItemInline,
        CostBreakdownInline
    ]
    model = Invoice
    form = InvoiceAdminForm

    list_display = ['id', 'number', 'name', 'date', 'contractor',
                    'hospital', 'net_value', 'gross_value', 'status', ]

    search_fields = ['net_value', 'gross_value', 'description', ]
    change_form_template = 'admin/dane/change_form.html'
    change_list_template = 'admin/dane/change_list.html'
    custom_filter_fields = ('external_service',)
    custom_combo_fields = ['contractor', 'hospital']
    readonly_fields = ('id', 'created_at', 'created_by')
    ordering = ("-id",)
    actions = ['export_invoices', 'export_cost_breakdown',
               'export_cost_center_summary', open_print_form]
    exportable_fields = ['id', 'number', 'status', 'name', 'date',
                         'contractor', 'hospital', 'net_value', 'gross_value', ]
    list_filter = ['id', 'number', 'name', 'date', 'contractor',
                   'hospital', 'net_value', 'gross_value', 'status', ]

    fieldsets = (
        (u"Szczegóły faktury", {
            'fields': (
                'id',
                'number',
                'name',
                'description',
                'date',
                'payment_date',
                'posting_date',
                'contractor',
                'hospital',
                'scan',
                'net_value',
                'gross_value',
                'created_at',
                'created_by',
                'status',
            )
        }),
        (u"Zlecenia", {
            "fields": ('external_service',), 'classes': ('open'),
        }),
    )

    class Media:
        css = {"all": ("css/hide_inline_original.css",)}

    def get_form(self, request, obj=None, **kwargs):
        form = super(InvoiceAdmin, self).get_form(request, obj, **kwargs)
        form.current_user = request.user
        if request.POST:
            if obj:
                form.invoiceiteminline = inlineformset_factory(
                    Invoice, InvoiceItem, form=InvoiceItemAdminForm)(request.POST, instance=obj)
                form.costbreakdowninline = inlineformset_factory(Invoice, CostBreakdown,
                                                                 form=CostBreakdownForm,
                                                                 exclude=['cost_center_name',
                                                                          'cost_center_description',
                                                                          'cost_center_symbol'])(request.POST,
                                                                                                 instance=obj)
        return form

    def export_invoices(self, request, queryset):
        exported_columns = None
        if hasattr(self, 'exportable_fields'):
            exported_columns = self.exportable_fields

        objects = []
        for invoice in queryset:
            objects.append(invoice)

        if len(objects) > 0:
            response = render_xls(self.opts.model_name,
                                  objects, exported_columns)
            return response
    export_invoices.short_description = _('Eksport do XLS')

    def export_cost_center_summary(self, request, queryset):
        header = (
            ('order', u'Lp.'),
            ('cost_center_symbol', u'Symbol Centrum Kosztowego'),
            ('cost_center_description', u'Opis Centrum Kosztowego'),
            ('cost_center_name', u'Nazwa Centrum Kosztowego'),
            ('posting_date', u'Data księgowania'),
            ('invoice_number', u'Numer faktury'),
            ('invoice_status', u'Status faktury'),
            ('invoice_name', u'Nazwa faktury'),
            ('invoice_date', u'Data faktury'),
            ('payment_date', u'Data płatności'),
            ('contractor', u'Kontrahent'),
            ('net_cost', u'Koszt netto'),
            ('gross_cost', u'Koszt brutto'),
        )
        objects = []
        i = 1
        for invoice in queryset:
            summary = CostCenterSummary(invoice)
            summary_rows = summary.compute_summary()

            for key in summary_rows:
                summary_row = summary_rows[key]
                row = {
                    'order': i,
                    'cost_center_symbol': summary_row.get('cost_center_symbol'),
                    'cost_center_description': summary_row.get('cost_center_description'),
                    'cost_center_name': summary_row.get('cost_center_name'),
                    'posting_date': invoice.posting_date,
                    'invoice_number': invoice.number,
                    'invoice_status': invoice.get_status_display(),
                    'invoice_name': invoice.name,
                    'invoice_date': invoice.date,
                    'payment_date': invoice.payment_date,
                    'contractor': invoice.contractor,
                    'net_cost': round(summary_row.get('net_cost'), 2),
                    'gross_cost': round(summary_row.get('gross_cost'), 2),
                }
                i += 1
                objects.append(row)

        if len(objects) > 0:
            response = render_list_xls(self.opts.model_name, objects, header)
            return response

    export_cost_center_summary.short_description = _(
        u'Eksport obciążenia Centrów Kosztowych do XLS')

    def export_cost_breakdown(self, request, queryset):

        header = (
            ('order', u'Lp.'),
            ('device_name', u'Nazwa urządzenia'),
            ('device_manufacturer', u'Producent urządzenia'),
            ('device_model', u'Model urządzenia'),
            ('device_serial_number', u'Numer seryjny urządzenia'),
            ('device_inventory_number', u'Numer inwentarzowy urządzenia'),
            ('invoice_number', u'Numer faktury'),
            ('invoice_status', u'Status faktury'),
            ('invoice_name', u'Nazwa faktury'),
            ('invoice_date', u'Data faktury'),
            ('payment_date', u'Data płatności'),
            ('issue_date', u'Data księgowania'),
            ('contractor', u'Kontrahent'),
            ('hospital', u'Szpital'),
            ('net_cost', u'Koszt netto'),
            ('gross_cost', u'Koszt brutto'),
            ('cost_center_symbol', u'Symbol Centrum Kosztowego'),
            ('cost_center_name', u'Nazwa Centrum Kosztowego'),

        )
        objects = []
        i = 1
        for invoice in queryset:
            breakdown = CostBreakdown.objects.filter(invoice=invoice)

            """ :type breakdown: list[CostBreakdown] """
            for breakdown_row in breakdown:
                row = {
                    'order': i,
                    'device_name': breakdown_row.device_name,
                    'device_manufacturer': breakdown_row.device_manufacturer,
                    'device_model': breakdown_row.device_model,
                    'device_serial_number': breakdown_row.device_serial_number,
                    'device_inventory_number': breakdown_row.device_inventory_number,
                    'invoice_number': invoice.number,
                    'invoice_status': invoice.get_status_display(),
                    'invoice_name': invoice.name,
                    'invoice_date': invoice.date,
                    'payment_date': invoice.payment_date,
                    'issue_date': invoice.posting_date,
                    'contractor': invoice.contractor,
                    'hospital': invoice.hospital,
                    'net_cost': round(breakdown_row.net_cost, 2),
                    'gross_cost': round(breakdown_row.gross_cost, 2),
                    'cost_center_symbol': breakdown_row.cost_center_symbol,
                    'cost_center_name': breakdown_row.cost_center_name,
                }
                i += 1
                objects.append(row)

        if len(objects) > 0:
            response = render_list_xls(self.opts.model_name, objects, header)
            return response

    export_cost_breakdown.short_description = _(u'Eksport kosztów do XLS')

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(InvoiceAdmin, self).get_fieldsets(request, obj)

        if not obj:
            fields = (
                'number',
                'name',
                'description',
                'date',
                'payment_date',
                'posting_date',
                'contractor',
                'hospital',
                'scan',
                'net_value',
                'gross_value',
            )

            fieldsets = (
                (u"Szczegóły faktury", {
                    'fields': fields
                }),
                (u"Zlecenia", {
                    "fields": ('external_service',), 'classes': ('open'),
                }),
            )

        return fieldsets

    def get_printed_fieldsets(self, requests, obj=None):
        fieldsets = (
            (u"Szczegóły faktury", [
                ('number', u"Numer"),
                ('name', u"Nazwa"),
                ('description', u"Opis"),
                ('date', u"Data faktury"),
                ('payment_date', u"Data zapłaty"),
                ('posting_date', u"Data księgowania"),
                ('contractor', u"Kontrahent"),
                ('hospital', u"Szpital"),
                ('scan', u"Skan"),
                ('net_value', u"Wartość netto"),
                ('gross_value', u"Wartość brutto"),
                ('created_at', u"Data dodania"),
                ('created_by', u"Utworzone przez"),
                ('status', u"Status"),
            ]),
            (u"Zlecenia", {
                ('external_service', u"Zlecenia"),
            }),
            (u'Pozycje faktury', [
                ('inline_InvoiceItem', u'Pozycje faktury')
            ]),
            (u'Podzia\u0142 koszt\xf3w', [
                ('inline_CostBreakdown', u'Podzia\u0142 koszt\xf3w')
            ]),
            (u"Podsumowanie", [
                ("invoice_summary", u"Podsumowanie",)
            ]),
        )
        return fieldsets

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_filter_fields'] = self.custom_filter_fields
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        extra_context['object'] = self.get_object(request, None)
        extra_context['content_type_model'] = 'invoice'

        return super(InvoiceAdmin, self).add_view(request, form_url, extra_context)

    def get_formsets(self, request, obj=None):
        for inline in self.get_inline_instances(request):
            # hide MyInline in the add view
            if isinstance(inline, CostBreakdownInline) and obj is None:
                continue
            yield inline.get_formset(request, obj)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_filter_fields'] = self.custom_filter_fields
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        obj = self.get_object(request, object_id)
        extra_context['object'] = obj
        extra_context['content_type_model'] = 'invoice'

        # Computing Cost Center Summary
        cost_summary = CostCenterSummary(obj)
        cost_center_summary = cost_summary.compute_summary()

        extra_context['cost_center_summary'] = cost_center_summary

        return super(InvoiceAdmin, self).change_view(request, object_id, form_url, extra_context)

    def save_formset(self, request, form, formset, change):
        if not change:
            net_value = 0
            gross_value = 0

            # because there are many form sets and we want to do certain action only for InvoiceItem formset
            invoice_item_formset = False
            for f in formset:
                item = f.instance
                if not isinstance(item, InvoiceItem):
                    continue

                if item.amount is None or item.net_price is None:
                    continue
                invoice_item_formset = True
                net_value += item.net_cost
                gross_value += item.gross_cost

            if invoice_item_formset:
                form.instance.net_value = net_value
                form.instance.gross_value = gross_value
                form.instance.save()

        return super(InvoiceAdmin, self).save_formset(request, form, formset, change)

    def save_related(self, request, form, formsets, change):

        result = super(InvoiceAdmin, self).save_related(
            request, form, formsets, change)
        service_is_changed = False

        selected_invoice_services = InvoiceService.objects.filter(
            invoice=form.instance)
        new_invoice_services = [
            int(service_id) for service_id in form.cleaned_data.get('external_service')]
        if set(new_invoice_services) - set(selected_invoice_services.values_list("service__id", flat=True)):
            CostBreakdown.objects.filter(invoice=form.instance).delete()
            service_is_changed = True

        selected_invoice_services.delete()
        for service_id in new_invoice_services:
            InvoiceService.objects.create(
                invoice=form.instance, service_id=service_id).save()

        if form.instance.has_costs_breakdown() and not form.invoice_item_was_changed:
            return result

        if not form.instance.is_accepted() or service_is_changed or form.invoice_item_was_changed:
            cost_breakdown_creator = CostBreakdownCreator(form.instance)
            cost_breakdown_creator.breakdown_costs()

        return result

    def save_form(self, request, form, change):

        if not change:
            form.instance.created_by = request.user
            form.instance.net_value = 0
            form.instance.gross_value = 0

        return super(InvoiceAdmin, self).save_form(request, form, change)

    def changelist_view(self, request, extra_context=None):
        if not request.user.has_perm('cmms.view_changelist_ticket'):
            raise PermissionDenied
        extra_context = {}
        extra_context['objects_name'] = [
            ('device', u'Urządzenia'), ('ticket', u'Zgłoszenia')]
        extra_context['current_list_name'] = 'invoice'

        form = AdvancedInvoiceFilter(request.POST.copy())
        last_filter_data = dict(form.data)
        last_filter = []
        for data in last_filter_data:
            key = "%s" % data
            last_filter.append({key: last_filter_data[data][0]})

        extra_context['last_data_filter'] = last_filter
        if request.method == "POST":
            extra_context['active_filter'] = True

        return super(InvoiceAdmin, self).changelist_view(request, extra_context)

    def get_urls(self):
        urls = super(InvoiceAdmin, self).get_urls()

        my_urls = [
re_path(r'^get_advanced_invoice_filter/$', 'dane.admin_views.get_advanced_invoice_filter',
                name='get_advanced_invoice_filter'),
        
]
        return my_urls + urls

    def get_queryset(self, request):
        filters = {}
        excludes = {}
        if request.method == 'POST':
            request_data = request.POST.copy()
            form = AdvancedInvoiceFilter(request_data)
            filter_data = dict(form.data)
            advanced_invoice_filter = form.data.get("advanced_invoice_filter")
            excluded_services = []
            filtered_services = []

            if advanced_invoice_filter is not None:
                for data in filter_data:

                    if filter_data[data] and filter_data[data][0] != '':
                        if data == 'ticket':
                            tickets_id = [
                                int(id) for id in filter_data[data][0].split(",")]
                            services = Service.objects.filter(
                                ticket__in=tickets_id)
                            services_id = [int(service.id)
                                           for service in services]

                            if filter_data['ticket_operator'][0] == '1':
                                for service_id in services_id:
                                    filtered_services.append(service_id)
                            elif filter_data['ticket_operator'][0] == '2':
                                for service_id in services_id:
                                    excluded_services.append(service_id)

                        if data == 'service':
                            if filter_data['service_operator'][0] == '1':
                                for service_id in [int(id) for id in filter_data[data][0].split(",")]:
                                    filtered_services.append(service_id)
                            elif filter_data['service_operator'][0] == '2':
                                for service_id in [int(id) for id in filter_data[data][0].split(",")]:
                                    excluded_services.append(service_id)

                        if data == 'device':
                            devices_id = [
                                int(id) for id in filter_data[data][0].split(",")]
                            tickets = Ticket.objects.filter(
                                device__in=devices_id)
                            tickets_id = [int(ticket.id) for ticket in tickets]
                            services = Service.objects.filter(
                                ticket__in=tickets_id)
                            services_id = []
                            for service in services:
                                services_id.append(service.id)

                            if filter_data['device_operator'][0] == '1':
                                for service_id in services_id:
                                    filtered_services.append(service_id)
                            elif filter_data['device_operator'][0] == '2':
                                for service_id in services_id:
                                    excluded_services.append(service_id)

                        if data == 'date':
                            if filter_data['date_operator'][0] == '1':
                                filters['date'] = filter_data[data][0]
                            elif filter_data['date_operator'][0] == '2':
                                filters['date__gte'] = filter_data[data][0]
                            elif filter_data['date_operator'][0] == '3':
                                filters['date__lte'] = filter_data[data][0]
                            elif filter_data['date_operator'][0] == '4':
                                filters['date__gt'] = filter_data[data][0]
                            elif filter_data['date_operator'][0] == '5':
                                filters['date__lt'] = filter_data[data][0]
                        if data == 'date_operator' and filter_data['date_operator'][0] == '6':
                            if filter_data["date_from"][0] != '' and filter_data["date_to"][0] != '':
                                filters['date__gte'] = filter_data["date_from"][0]
                                filters['date__lt'] = filter_data["date_to"][0]
                        if data == 'date_operator' and filter_data['date_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['date__gte'] = now_minus_seven_days
                        if data == 'name':
                            if filter_data['name_operator'][0] == '1':
                                filters['name__icontains'] = filter_data[data][0]
                            elif filter_data['name_operator'][0] == '2':
                                excludes['name__icontains'] = filter_data[data][0]
                        if data == 'number':
                            if filter_data['number_operator'][0] == '1':
                                filters['number__icontains'] = filter_data[data][0]
                            elif filter_data['name_operator'][0] == '2':
                                excludes['number__icontains'] = filter_data[data][0]
                        if data == 'net_value':
                            if filter_data['net_value_operator'][0] == '1':
                                filters['net_value'] = filter_data[data][0]
                            elif filter_data['net_value_operator'][0] == '2':
                                filters['net_value__gte'] = filter_data[data][0]
                            elif filter_data['net_value_operator'][0] == '3':
                                filters['net_value__lte'] = filter_data[data][0]
                            elif filter_data['net_value_operator'][0] == '4':
                                filters['net_value__gt'] = filter_data[data][0]
                            elif filter_data['net_value_operator'][0] == '5':
                                filters['net_value__lt'] = filter_data[data][0]
                        if data == 'gross_value':
                            if filter_data['gross_value_operator'][0] == '1':
                                filters['gross_value'] = filter_data[data][0]
                            elif filter_data['gross_value_operator'][0] == '2':
                                filters['gross_value__gte'] = filter_data[data][0]
                            elif filter_data['gross_value_operator'][0] == '3':
                                filters['gross_value__lte'] = filter_data[data][0]
                            elif filter_data['gross_value_operator'][0] == '4':
                                filters['gross_value__gt'] = filter_data[data][0]
                            elif filter_data['gross_value_operator'][0] == '5':
                                filters['gross_value__lt'] = filter_data[data][0]
                        if data == 'status':
                            if filter_data['status_operator'][0] == '1':
                                filters['status'] = filter_data[data][0]
                            elif filter_data['status_operator'][0] == '2':
                                excludes['status'] = filter_data[data][0]
                        if data == 'contractor':
                            if filter_data['contractor_operator'][0] == '1':
                                filters['contractor__name__icontains'] = filter_data[data][0]
                            elif filter_data['contractor_operator'][0] == '2':
                                excludes['contractor__name__icontains'] = filter_data[data][0]
                        if data == 'hospital':
                            if filter_data['hospital_operator'][0] == '1':
                                filters['hospital__name__icontains'] = filter_data[data][0]
                            elif filter_data['hospital_operator'][0] == '2':
                                excludes['hospital__name__icontains'] = filter_data[data][0]

            if filtered_services:
                filters['invoiceservice__service__in'] = filtered_services
            if excluded_services:
                excludes['invoiceservice__service__in'] = excluded_services

            invoices = Invoice.objects.filter(**filters).exclude(**excludes)

            return invoices
        else:
            return super(InvoiceAdmin, self).get_queryset(request)


class LocationAdmin(admin.ModelAdmin):
    model = Location
    exclude = ("staff_pks", )
    list_display = ['name', 'description', 'person',
                    'street', 'street_number', 'postal_code', 'city']
    search_fields = ['name', 'description', 'person__username', 'person__email',
                     'person__first_name', 'person__last_name', 'street', 'postal_code', 'city', 'email', ]
    list_filter = ['person', ]
    filter_horizontal = ('staff', )
    ordering = ("name",)
    change_form_template = 'admin/dane/change_form.html'
    change_list_template = 'admin/dane/change_list.html'

    def __get_object(self, request):
        object_id = request.META['PATH_INFO'].strip('/').split('/')[-1]
        try:
            object_id = int(object_id)
        except ValueError:
            return None
        return self.model.objects.get(pk=object_id)

    def save_related(self, request, form, formsets, change):
        try:
            location = self.__get_object(request)
            staff_delta = ()

            old_staff = list(location.staff.all())
            new_staff = list(form.cleaned_data['staff'])

            # check if permissions have changed
            staff_changed = old_staff != new_staff

            if staff_changed:
                staff_delta = [x for x in old_staff +
                               new_staff if x not in old_staff or x not in new_staff]
                staff_delta = [i.pk for i in staff_delta]

            users = UserProfile.objects.filter(
                Q(staff=location) | Q(person=location) | Q(id__in=staff_delta))
        except:
            staff_changed = False
            pass

        super(LocationAdmin, self).save_related(
            request, form, formsets, change)

        # TOOD: check if device permissions changed before changing anything
        # update permissions
        if staff_changed:
            for user in users:
                view_all_devices = user.has_perm("cmms.view_all_devices")

                # update permissions for devices
                if view_all_devices:
                    user_devices = Device.objects.all()
                else:
                    user_devices = Device.objects.filter(
                        Q(location=location) | Q(person_responsible=user))

                # get list of devices to reset
                reset_devices = get_objects_for_user(
                    user, 'cmms.view_device', accept_global_perms=False) | user_devices

                # push task
                setup_permissions.delay(user.pk, [i.pk for i in reset_devices], [
                                        i.pk for i in user_devices])


class DocumentAdmin(GuardedModelAdmin, SimpleHistoryAdmin):
    model = Document
    list_display = ['name', 'sort', 'timestamp', 'date_document', ]
    search_fields = ['name', 'device__name', 'description', ]
    list_filter = ['sort', 'device', 'service', 'ticket']
    change_form_template = 'admin/guardian/model/change_form.html'
    change_list_template = 'admin/dane/change_list.html'
    filter_horizontal = ('device', 'service', 'ticket', )
    custom_filter_fields = ('device', 'service', 'ticket')
    custom_combo_fields = ['person_adding', 'contractor', ]
    ordering = ("-id",)
    fieldsets = (
        (u"Powiązane obiekty", {"fields": (
            'device',
            'ticket',
            'service',
        ), 'classes': ('collapse', ), }),
        (u"Ogólne", {"fields": (
            'name',
            'description',
            'date_document',
            'number',
            'date_expiration',
            'date_termination',
            'person_adding',
            'contractor',
            'access'
        ), }),
        (u"Obraz", {"fields": (
            'sort',
                    'scan',
                    ), }),
    )
    readonly_fields = ('person_adding',)
    form = DocumentAdminForm

    def get_form(self, request, obj=None):
        form = super(DocumentAdmin, self).get_form(request, obj)
        form.current_user = request.user
        return form

    def add_view(self, request, form_url='', extra_context=None):

        extra_context = {}
        extra_context['custom_filter_fields'] = self.custom_filter_fields
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        extra_context['object'] = self.get_object(request, None)
        extra_context['content_type_model'] = 'document'

        return super(DocumentAdmin, self).add_view(request, form_url, extra_context)

    def response_add(self, request, obj, post_url_continue='../%s/'):
        device_id = request.GET.get('device_id', '')
        if device_id:  # when adding from service screen (bottom table)
            obj.device.add(int(device_id))
            return HttpResponse('<script type="text/javascript">opener.load_device_documents(); window.close();</script>')
        post_url_continue = "../%s/" % obj.pk
        resp = super(DocumentAdmin, self).response_add(
            request, obj, post_url_continue)
        return resp

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_filter_fields'] = self.custom_filter_fields
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        extra_context['object'] = self.get_object(request, object_id)

        return super(DocumentAdmin, self).change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        if not request.user.has_perm('cmms.view_changelist_document'):
            raise PermissionDenied
        extra_context = {}
        extra_context['objects_name'] = [
            ('service', 'Zlecenia'), ('ticket', u'Zgłoszenia'), ('device', u'Urządzenia')]
        extra_context['current_list_name'] = 'document'

        form = AdvancedDocumentFilter(request.POST.copy())
        last_filter_data = dict(form.data)
        last_filter = []
        for data in last_filter_data:
            key = "%s" % data
            last_filter.append({key: last_filter_data[data][0]})

        extra_context['last_data_filter'] = last_filter
        if request.method == "POST":
            extra_context['active_filter'] = True

        return super(DocumentAdmin, self).changelist_view(request, extra_context)

    def get_queryset(self, request):
        filters = {}
        excludes = {}

        documents = super(DocumentAdmin, self).get_queryset(request).\
                        for_user(request.user)
        if request.method == 'POST':
            request_data = request.POST.copy()
            form = AdvancedDocumentFilter(request_data)
            filter_data = dict(form.data)
            advanced_document_filter = form.data.get(
                "advanced_document_filter")

            if advanced_document_filter:
                for data in filter_data:
                    if filter_data[data] and filter_data[data][0] != '':
                        if data == 'ticket':
                            if filter_data['ticket_operator'][0] == '1':
                                filters['ticket__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]
                            elif filter_data['ticket_operator'][0] == '2':
                                excludes['ticket__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]

                        if data == 'service':
                            if filter_data['service_operator'][0] == '1':
                                filters['service__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]
                            elif filter_data['service_operator'][0] == '2':
                                excludes['service__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]

                        if data == 'device':
                            if filter_data['device_operator'][0] == '1':
                                filters['device__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]
                            elif filter_data['device_operator'][0] == '2':
                                excludes['device__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]

                        if data == 'date_add':
                            if filter_data['date_add_operator'][0] == '1':
                                filters['timestamp'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '2':
                                filters['timestamp__gte'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '3':
                                filters['timestamp__lte'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '4':
                                filters['timestamp__gt'] = filter_data[data][0]
                            elif filter_data['date_add_operator'][0] == '5':
                                filters['timestamp__lt'] = filter_data[data][0]
                        if data == 'date_add_operator' and filter_data['date_add_operator'][0] == '6':
                            if filter_data["date_add_from"][0] != '' and filter_data["date_add_to"][0] != '':
                                filters['timestamp__gte'] = filter_data["date_add_from"][0]
                                filters['timestamp__lt'] = filter_data["date_add_to"][0]
                        if data == 'date_add_operator' and filter_data['date_add_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['timestamp__gte'] = now_minus_seven_days

                        if data == 'date_document':
                            if filter_data['date_document_operator'][0] == '1':
                                filters['date_document'] = filter_data[data][0]
                            elif filter_data['date_document_operator'][0] == '2':
                                filters['date_document__gte'] = filter_data[data][0]
                            elif filter_data['date_document_operator'][0] == '3':
                                filters['date_document__lte'] = filter_data[data][0]
                            elif filter_data['date_document_operator'][0] == '4':
                                filters['date_document__gt'] = filter_data[data][0]
                            elif filter_data['date_document_operator'][0] == '5':
                                filters['date_document__lt'] = filter_data[data][0]
                        if data == 'date_document_operator' and filter_data['date_document_operator'][0] == '6':
                            if filter_data["date_document_from"][0] != '' and filter_data["date_document_to"][0] != '':
                                filters['date_document__gte'] = filter_data["date_document_from"][0]
                                filters['date_document__lt'] = filter_data["date_document_to"][0]
                        if data == 'date_document_operator' and filter_data['date_document_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['date_document__gte'] = now_minus_seven_days

                        if data == 'date_expiration':
                            if filter_data['date_expiration_operator'][0] == '1':
                                filters['date_expiration'] = filter_data[data][0]
                            elif filter_data['date_expiration_operator'][0] == '2':
                                filters['date_expiration__gte'] = filter_data[data][0]
                            elif filter_data['date_expiration_operator'][0] == '3':
                                filters['date_expiration__lte'] = filter_data[data][0]
                            elif filter_data['date_expiration_operator'][0] == '4':
                                filters['date_expiration__gt'] = filter_data[data][0]
                            elif filter_data['date_expiration_operator'][0] == '5':
                                filters['date_expiration__lt'] = filter_data[data][0]
                        if data == 'date_expiration_operator' and filter_data['date_expiration_operator'][0] == '6':
                            if filter_data["date_expiration_from"][0] != '' and filter_data["date_expiration_to"][0] != '':
                                filters['date_expiration__gte'] = filter_data["date_expiration_from"][0]
                                filters['date_expiration__lt'] = filter_data["date_expiration_to"][0]
                        if data == 'date_expiration_operator' and filter_data['date_expiration_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['date_expiration__gte'] = now_minus_seven_days

                        if data == 'description':
                            if filter_data['description_operator'][0] == '1':
                                filters['description__icontains'] = filter_data[data][0]
                            elif filter_data['description_operator'][0] == '2':
                                excludes['description__icontains'] = filter_data[data][0]

                        if data == 'number':
                            if filter_data['number_operator'][0] == '1':
                                filters['number__icontains'] = filter_data[data][0]
                            elif filter_data['number_operator'][0] == '2':
                                excludes['number__icontains'] = filter_data[data][0]

                        if data == 'name':
                            if filter_data['name_operator'][0] == '1':
                                filters['name__icontains'] = filter_data[data][0]
                            elif filter_data['name_operator'][0] == '2':
                                excludes['name__icontains'] = filter_data[data][0]

                        if data == 'sort':
                            if filter_data['sort_operator'][0] == '1':
                                filters['sort'] = filter_data[data][0]
                            elif filter_data['sort_operator'][0] == '2':
                                excludes['sort'] = filter_data[data][0]

                        if data == 'access':
                            if filter_data['access_operator'][0] == '1':
                                filters['access'] = filter_data[data][0]
                            elif filter_data['access_operator'][0] == '2':
                                excludes['access'] = filter_data[data][0]

                        if data == 'person_adding':
                            if filter_data['person_adding_operator'][0] == '1':
                                filters['person_adding'] = filter_data[data][0]
                            elif filter_data['person_adding_operator'][0] == '2':
                                excludes['person_adding'] = filter_data[data][0]

                        if data == 'contractor':
                            if filter_data['contractor_operator'][0] == '1':
                                filters['contractor__name__icontains'] = filter_data[data][0]
                            elif filter_data['contractor_operator'][0] == '2':
                                excludes['contractor__name__icontains'] = filter_data[data][0]

            documents = documents.filter(**filters).exclude(**excludes)

        return documents.distinct()

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(DocumentAdmin, self).get_fieldsets(request, obj)

        if obj is None:
            remove_from_fieldsets(fieldsets, ('person_adding',))

        return fieldsets

    def get_urls(self):

        urls = super(DocumentAdmin, self).get_urls()

        my_urls = [
re_path(r'^get_advanced_document_filter/$',
                'dane.admin_views.get_advanced_document_filter', name='get_advanced_document_filter'),
            re_path(r'^get_contractor/$', 'dane.admin_views.get_contractor',
                name='get_contractor'),
        
]
        return my_urls + urls


class UserProfileChangeForm(UserChangeForm):

    class Meta:
        model = get_user_model()
        exclude = []


class UserProfileCreationForm(UserCreationForm):

    class Meta:
        model = get_user_model()
        exclude = []

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            get_user_model().objects.get(username=username)
        except get_user_model().DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])


class UserProfileAdmin(PermissionFilterMixin, UserAdmin):
    model = UserProfile

    form = UserProfileChangeForm
    add_form = UserProfileCreationForm

    def get_groups(self):
        groups = self.groups.all()
        arr = []
        for g in groups:
            arr.append(
                "<nobr><a href=\"/a/auth/group/%s\">%s</a></nobr>" % (g.pk, g.name))
        return ", ".join(arr)
    get_groups.short_description = u"Grupy"
    get_groups.allow_tags = True

    list_display = ['username', 'first_name', 'last_name',
                    get_groups, 'email', 'is_active', 'phone']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    list_filter = ['is_active', 'groups']
    change_form_template = 'admin/dane/change_form.html'
    change_list_template = 'admin/dane/change_list.html'
    fieldsets = UserAdmin.fieldsets
    #fieldsets =+ (_('Important dates'), {'fields': ('last_login', 'date_joined')}),

    fieldsets += (("Skany", {'fields': ('stamp', 'signature', )}),
                  ("Telefony", {'fields': ('phone', )}), )

    def save_related(self, request, form, formsets, change):
        user = UserProfile.objects.get(username=form.cleaned_data['username'])

        # check if groups have changed
        try:
            groups_changed = user.groups.all() != form.cleaned_data['groups']
            permissions_changed = user.user_permissions.all(
            ) != form.cleaned_data['user_permissions']
        except:
            groups_changed = False
            permissions_changed = False

        super(UserProfileAdmin, self).save_related(
            request, form, formsets, change)

        # TOOD: check if device permissions changed before changing anything
        # update permissions
        if groups_changed or permissions_changed:
            view_all_devices = user.has_perm("cmms.view_all_devices")

            # get all locations for user and devices he/her should see
            usr_locations = user.staff.all() | user.person.all()

            # update permissions for devices
            if view_all_devices:
                user_devices = Device.objects.all()
            else:
                user_devices = Device.objects.filter(
                    Q(location__in=usr_locations) | Q(person_responsible=user))

            # get list of devices to reset
            reset_devices = get_objects_for_user(
                user, 'cmms.view_device', accept_global_perms=False) | user_devices

            # push task
            setup_permissions.delay(user.pk, [i.pk for i in reset_devices], [
                                    i.pk for i in user_devices])


class GroupAdmin(PermissionFilterMixin, admin.ModelAdmin):
    model = Group
    change_form_template = 'admin/dane/change_form.html'
    change_list_template = 'admin/dane/change_list.html'
    filter_horizontal = ('permissions', )

    def __get_object(self, request):
        object_id = request.META['PATH_INFO'].strip('/').split('/')[-1]
        try:
            object_id = int(object_id)
        except ValueError:
            return None
        return self.model.objects.get(pk=object_id)

    def save_related(self, request, form, formsets, change):
        try:
            group = self.__get_object(request)
            users = UserProfile.objects.filter(groups=group)

            # check if permissions have changed
            permissions_changed = group.permissions.all(
            ) != form.cleaned_data['permissions']
        except:
            permissions_changed = False
            pass

        super(GroupAdmin, self).save_related(request, form, formsets, change)

        # TOOD: check if device permissions changed before changing anything
        # update permissions
        if permissions_changed:
            for user in users:
                view_all_devices = user.has_perm("cmms.view_all_devices")

                # get all locations for user and devices he/her should see
                usr_locations = user.staff.all() | user.person.all()

                # update permissions for devices
                if view_all_devices:
                    user_devices = Device.objects.all()
                else:
                    user_devices = Device.objects.filter(
                        Q(location__in=usr_locations) | Q(person_responsible=user))

                # get list of devices to reset
                reset_devices = get_objects_for_user(
                    user, 'cmms.view_device', accept_global_perms=False) | user_devices

                # push task
                setup_permissions.delay(user.pk, [i.pk for i in reset_devices], [
                                        i.pk for i in user_devices])


class HospitalAdmin(admin.ModelAdmin):
    model = Hospital
    list_display = ['name', 'NIP', ]
    search_fields = ['name', 'NIP', ]
    change_form_template = 'admin/dane/change_form.html'
    change_list_template = 'admin/dane/change_list.html'

    fieldsets = (
        (u"Dane podstawowe", {"fields": (
            'name',
            'street',
            'street_number',
            'postal_code',
            'city',
            'logo'
        ), }),
        (u"Numery", {"fields": (
            'NIP',
            'REGON',
            'KRS',
        ), 'classes': ('collapse', ), }),
        (u"Dane kontaktowe", {"fields": (
            'telephone',
            'fax',
            'email',
        ), }),
    )


class DaneAdminSite(AdminSite):
    pass


class InspectionDeviceInline(admin.TabularInline):
    model = InspectionDevice


class InspectionDocumentInline(admin.TabularInline):
    model = InspectionDocument


class InspectionItemInline(admin.TabularInline):
    model = InspectionItem
    fields = ["name", "planned_date", "ticket_date", "added_user"]


class InspectionAdmin(admin.ModelAdmin):
    inlines = [InspectionDeviceInline,
               InspectionDocumentInline, InspectionItemInline]
    list_display = ["id", "name", "type", "cycle_date_start"]
    change_list_template = 'admin/dane/change_list.html'
    change_form_template = 'admin/dane/change_form.html'
    ordering = ("-id",)
    custom_combo_fields = ['added_user']

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        extra_context['object'] = self.get_object(request, None)
        extra_context['content_type_model'] = 'inspection'

        return super(InspectionAdmin, self).add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        extra_context['object'] = self.get_object(request, object_id)
        extra_context['content_type_model'] = 'inspection'

        return super(InspectionAdmin, self).change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        extra_context = {"is_inspection": True}
        return super(InspectionAdmin, self).changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        obj.added_user = request.user
        return super(InspectionAdmin, self).save_model(request, obj, form, change)


class CalendarEventAdmin(admin.ModelAdmin):
    model = CalendarEvent
    form = CalendarEventAdminForm


class MileageAdmin(GuardedModelAdmin, SimpleHistoryAdmin):
    model = Mileage
    form = MileageAdminForm
    show_history = True

    def get_form(self, request, obj=None, **kwargs):
        form = super(MileageAdmin, self).get_form(request, obj, **kwargs)
        form.current_user = request.user
        return form

    def get_urls(self):
        urls = super(MileageAdmin, self).get_urls()

        my_urls = [
re_path(r'^get_advanced_mileage_filter/$', 'dane.admin_views.get_advanced_mileage_filter',
                name='get_advanced_mileage_filter'),
        
]
        return my_urls + urls

    def get_device(self):
        d = self.device
        return "%s: <a href=\"/a/cmms/device/%s\">%s</a>" % (d.inventory_number, d.pk, d.name)
    get_device.short_description = u"Urządzenia"
    get_device.allow_tags = True

    def reset_mileage(modeladmin, request, queryset):
        user = request.user

        for mileage in queryset:
            mileage.state = mileage.state_initial
            mileage.save()
            history = mileage.history.all()[0]
            history.remarks = 'Zresetowano licznik'
            history.save()

        return None
    reset_mileage.short_description = _('Wyzeruj licznik')

    actions = [export_model_to_xls, reset_mileage, open_print_form]

    exportable_fields = ['id', 'name', 'status', 'unit', 'get_device', 'state_initial', 'state',
                         'get_percentage', 'state_max', 'state_warning', 'warning', 'date', 'person_creating', 'remarks', ]

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_filter_fields'] = self.custom_filter_fields
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        extra_context['single_device'] = True
        extra_context['content_type_model'] = 'mileage'

        return super(MileageAdmin, self).add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = {}
        extra_context['custom_filter_fields'] = self.custom_filter_fields
        extra_context['custom_combo_fields'] = self.custom_combo_fields
        extra_context['single_device'] = True
        extra_context['show_history'] = self.show_history
        extra_context['object'] = self.get_object(request, object_id)
        extra_context['content_type_model'] = 'mileage'

        return super(MileageAdmin, self).change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        if not request.user.has_perm('cmms.view_changelist_mileage'):
            raise PermissionDenied
        extra_context = {}
        extra_context['objects_name'] = [('mileage', u'Liczniki')]
        extra_context['current_list_name'] = 'mileage'

        form = AdvancedMileageFilter(request.POST.copy())
        last_filter_data = dict(form.data)
        last_filter = []
        for data in last_filter_data:
            key = "%s" % data
            last_filter.append({key: last_filter_data[data][0]})

        extra_context['last_data_filter'] = last_filter
        if request.method == "POST":
            extra_context['active_filter'] = True

        return super(MileageAdmin, self).changelist_view(request, extra_context)

    def get_queryset(self, request):
        filters = {}
        excludes = {}
        user = request.user
        if request.method == 'POST':
            request_data = request.POST.copy()
            form = AdvancedMileageFilter(request_data)
            filter_data = dict(form.data)
            advanced_mileage_filter = form.data.get("advanced_mileage_filter")

            if advanced_mileage_filter:
                for data in filter_data:
                    if filter_data[data] and filter_data[data][0] != '':
                        if data == 'device':
                            if filter_data['device_operator'][0] == '1':
                                filters['device__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]
                            elif filter_data['device_operator'][0] == '2':
                                excludes['device__in'] = [
                                    int(id) for id in filter_data[data][0].split(",")]

                        if data == 'date':
                            if filter_data['date_operator'][0] == '1':
                                filters['timestamp'] = filter_data[data][0]
                            elif filter_data['date_operator'][0] == '2':
                                filters['timestamp__gte'] = filter_data[data][0]
                            elif filter_data['date_operator'][0] == '3':
                                filters['timestamp__lte'] = filter_data[data][0]
                            elif filter_data['date_operator'][0] == '4':
                                filters['timestamp__gt'] = filter_data[data][0]
                            elif filter_data['date_operator'][0] == '5':
                                filters['timestamp__lt'] = filter_data[data][0]
                        if data == 'date_operator' and filter_data['date_operator'][0] == '6':
                            if filter_data["date_from"][0] != '' and filter_data["date_to"][0] != '':
                                filters['timestamp__gte'] = filter_data["date_from"][0]
                                filters['timestamp__lt'] = filter_data["date_to"][0]
                        if data == 'date_operator' and filter_data['date_operator'][0] == '7':
                            now = datetime.datetime.now()
                            now_minus_seven_days = now - relativedelta(days=7)
                            filters['timestamp__gte'] = now_minus_seven_days

                        if data == 'unit':
                            if filter_data['unit_operator'][0] == '1':
                                filters['unit'] = filter_data[data][0]
                            elif filter_data['unit_operator'][0] == '2':
                                excludes['unit'] = filter_data[data][0]

                        if data == 'status':
                            if filter_data['status_operator'][0] == '1':
                                filters['status'] = filter_data[data][0]
                            elif filter_data['status_operator'][0] == '2':
                                excludes['status'] = filter_data[data][0]

            mileages = Mileage.objects.filter(**filters).exclude(**excludes)
        else:
            mileages = super(MileageAdmin, self).get_queryset(request)
            devices = get_objects_for_user(
                user, "cmms.view_device", accept_global_perms=False)
            mileages = mileages.filter(device__in=devices)

        return mileages

    readonly_fields = ("date", "person_creating", "get_percentage",)

    list_display = ['id', 'name', 'status', get_device, 'unit',
                    'state', 'get_percentage', 'state_max', 'date', ]
    list_display_links = ['id', 'name', ]
    search_fields = ['name', 'device__name', 'device__genre__name', 'status']
    list_filter = ['device', 'name']
    change_form_template = 'admin/guardian/model/change_form.html'
    change_list_template = 'admin/dane/change_list.html'
    custom_filter_fields = ('device',)
    custom_combo_fields = ['unit']
    ordering = ("-id",)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(MileageAdmin, self).get_fieldsets(request, obj)

        # reset readonly_fields
        self.readonly_fields = ("date", "person_creating", "get_percentage",)

        if obj is None:
            remove_from_fieldsets(
                fieldsets, ('person_creating', 'date', 'get_percentage'))

        if not request.user.has_perm('cmms.change_mileage'):
            self.readonly_fields += ('name', 'unit', 'status', 'remarks',
                                     'state_initial', 'state_max', 'state_warning', 'warning')

        if not request.user.has_perm('cmms.update_mileage'):
            self.readonly_fields += ('state',)

        return fieldsets

    fieldsets = (
        (u"Powiązane urządzenie", {"fields": ('device',), }),
        (u"Dane licznika", {"fields": ('date', 'person_creating', 'name',
                                       'unit', 'status', 'remarks', 'state_initial', 'state_max',), }),
        (u"Wartość aktualna", {"fields": ('state', 'get_percentage',), }),
        (u"Monity", {"fields": ('state_warning', 'warning',), }),
    )


dane_admin = DaneAdminSite(name="dane_admin")

# TODO: remove this
dane_admin.register(Permission, PermissionAdmin)

dane_admin.register(Unit, UnitAdmin)
dane_admin.register(DevicePassport, DevicePassportAdmin)
dane_admin.register(Device, DeviceAdmin)

# dane_admin.register(Genre, GenreAdmin)
# dane_admin.register(Make, MakeAdmin)
# dane_admin.register(Mileage, MileageAdmin)
# dane_admin.register(Contractor, ContractorAdmin)
# dane_admin.register(CostCentre, CostCentreAdmin)
# dane_admin.register(Invoice, InvoiceAdmin)
# dane_admin.register(Location, LocationAdmin)
# dane_admin.register(Ticket, TicketAdmin)
# dane_admin.register(Service, ServiceAdmin)
# dane_admin.register(Document, DocumentAdmin)
# dane_admin.register(UserProfile, UserProfileAdmin)
# dane_admin.register(Group, GroupAdmin)
# dane_admin.register(Hospital, HospitalAdmin)
# dane_admin.register(Inspection, InspectionAdmin)
# dane_admin.register(CalendarEvent, CalendarEventAdmin)
