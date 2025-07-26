import datetime

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render
from django.template.defaultfilters import lower
from django.template.loader import render_to_string, get_template
from django.test import RequestFactory
from django.utils.decorators import method_decorator
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View
from django_comments.models import Comment
#from utils.forms import PDFForm
import os
from django.conf import settings
from django.contrib.staticfiles import finders
from xhtml2pdf import pisa
from xlwt import Workbook

from cmms.models import Service, Document, Device
from utils.logic import get_field_properties
from utils.tasks import send_service_email

User = get_user_model()


# Mapowanie model_name na szablon PDF

def print_admin(request, model_name):
    from dane import admin

    try:
        model = ContentType.objects.get(model=model_name.lower()).model_class()
        admin_object = admin.dane_admin._registry[model]
    except ContentType.DoesNotExist:
        raise Http404(f"Model '{model_name}' nie istnieje.")
    except KeyError:
        raise Http404(f"Admin dla modelu '{model_name}' nie jest zarejestrowany.")

    object_pks = request.GET.get("objects")
    if not object_pks:
        raise Http404("Brak podanych obiektów do wydruku.")
    object_pks = object_pks.split(",")

    objects = []
    for pk in object_pks:
        try:
            obj = model.objects.get(pk=int(pk))
            objects.append(obj)
        except (ValueError, model.DoesNotExist):
            raise Http404(f"Obiekt o PK={pk} nie istnieje.")

    try:
        fieldsets = admin_object.get_printed_fieldsets(request, objects[0])
    except AttributeError:
        # fallback: zbuduj fieldsets z get_fieldsets
        original_fieldsets = admin_object.get_fieldsets(request, objects[0])
        fieldsets = []
        for fieldset in original_fieldsets:
            fieldset_name, fieldset_options = fieldset
            fieldset_fields = []
            for field in fieldset_options.get('fields', []):
                try:
                    _field = objects[0]._meta.get_field(field)
                    verbose = str(_field.verbose_name)
                except Exception:
                    verbose = getattr(getattr(objects[0], field, None), 'short_description', field)
                fieldset_fields.append((field, verbose))
            fieldsets.append((fieldset_name, fieldset_fields))

        inlines = admin_object.get_inline_instances(request)
        excluded_inlines = getattr(admin_object, 'excluded_inlines', [])
        for inline in inlines:
            if inline.model.__name__ not in excluded_inlines:
                fieldsets.append((inline.verbose_name, [(f"inline_{inline.model.__name__}", inline.verbose_name)]))

        if model_name in ("ticket", "service"):
            fieldsets.append(("Komentarze", [("comments", "Komentarze")]))
        if getattr(admin_object, 'show_history', False):
            fieldsets.append(("Historia", [("history", "Historia zmian")]))

    default_selected = getattr(admin_object, 'get_default_selected', lambda r, o=None: [])(request, objects[0])
    custom_filter_fields = getattr(admin_object, 'custom_filter_fields', [])

    if request.method == 'POST':
        request_data = dict(request.POST.lists())

        show_comments = False
        show_history = False
        show_external_services = False
        show_invoice_summary = False
        show_costbreakdown = False

        inlines_selected = []
        selected_fieldsets = {}

        for key, values in request_data.items():
            if key.startswith("fields_"):
                section = key[7:]
                if section == "Komentarze" and "comments" in values:
                    show_comments = True
                elif section == "Historia" and "history" in values:
                    show_history = True
                elif section == "Zlecenia" and model_name == "invoice" and "external_service" in values:
                    show_external_services = True
                elif section == "Podsumowanie" and model_name == "invoice" and "invoice_summary" in values:
                    show_invoice_summary = True
                else:
                    inlines_selected += [v[7:] for v in values if v.startswith("inline_")]
                    fields = [v for v in values if not v.startswith("inline_")]
                    selected_fieldsets[section] = {"fields": tuple(fields)}
                    if "inline_CostBreakdown" in values:
                        show_costbreakdown = True

        rendered = []
        rf = RequestFactory()

        for obj in objects:
            fake_request = rf.get("/")
            fake_request.user = request.user
            fake_request.session = request.session
            fake_request.GET = request.GET.copy()

            response = admin_object.change_view(fake_request, str(obj.pk))
            response.template_name = 'admin/dane/pdf_change_form.html'

            adminform = response.context_data['adminform']
            try:
                adminform.readonly_fields = tuple(adminform.form.fields.keys())
            except Exception:
                adminform.readonly_fields = adminform

            # wyodrębnij tylko wybrane sekcje
            obj_selected_fieldsets = []
            for name, fieldset in adminform.fieldsets:
                if name in selected_fieldsets:
                    fields_in_section = selected_fieldsets[name]["fields"]
                    obj_selected_fieldsets.append((name, {"fields": fields_in_section}))

            # inline'y
            inline_formsets = [
                formset for formset in response.context_data.get('inline_admin_formsets', [])
                if formset.opts.model.__name__ in inlines_selected
                and formset.opts.model.__name__ not in getattr(admin_object, 'excluded_inlines', [])
            ]

            for formset in inline_formsets:
                formset.readonly_fields = formset.fieldsets[0][1].get('fields', [])
                if formset.formset.model._meta.model_name == "devicepassport":
                    allowed_fields = ("added_date", "content", "added_user")

                    for form in formset.formset.forms:
                        for name in list(form.fields):
                            if name not in allowed_fields:
                                form.fields.pop(name, None)
                        form.initial = {k: v for k, v in form.initial.items() if k in allowed_fields}
                formset.formset.can_delete = False
                formset.formset.can_add = False
                formset.formset.hide_scan = True
                formset.original = False
                for _ in range(formset.formset.extra):
                    try:
                        formset.formset.forms.pop()
                    except IndexError:
                        pass
                if formset.formset.model._meta.model_name == "costbreakdown" and not show_costbreakdown:
                    inline_formsets.remove(formset)

            field_values = {}
            for section in selected_fieldsets.values():
                for field_name in section["fields"]:
                    try:
                        field_object = obj._meta.get_field(field_name)
                        value = getattr(obj, field_name)

                        if field_object.is_relation:
                            if value is None:
                                field_values[field_name] = "–"
                            elif field_object.many_to_many:
                                field_values[field_name] = ", ".join(str(v) for v in value.all())
                            else:
                                field_values[field_name] = str(value)
                        else:
                            field_values[field_name] = value

                    except Exception:
                        try:
                            value = getattr(obj, field_name)
                            field_values[field_name] = str(value) if value is not None else "–"
                        except Exception:
                            field_values[field_name] = "–"

            response.context_data.update({
                'printed_fieldsets': obj_selected_fieldsets,
                'field_values': field_values,
                'inline_admin_formsets': inline_formsets,
                'show_comments': show_comments,
                'show_external_services': show_external_services,
                'show_invoice_summary': show_invoice_summary,
                'model_verbose': model._meta.verbose_name,
                'object': obj,
            })

            response.render()
            absolute_path = f"{request.META.get('HTTP_ORIGIN')}/site_media"
            content = response.rendered_content.replace('/site_media', absolute_path)
            rendered.append(mark_safe(content))

        html_string = render_to_string('pdf_preparation/pdf_admin_wrapper.html', {'rendered': rendered, 'user': request.user})
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="document.pdf"'

        def link_callback(uri, rel):
            """
            Przetwarza ścieżki /static/... oraz /media/... na rzeczywiste ścieżki systemowe.
            """
            # ścieżka do pliku statycznego (np. czcionki)
            if uri.startswith('/static/'):
                path = finders.find(uri.replace('/static/', ''))
                if path:
                    return path

            # ścieżka do mediów (np. załączniki)
            if uri.startswith(settings.MEDIA_URL):
                path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ''))
                if os.path.isfile(path):
                    return path

            # absolutna ścieżka jako fallback
            if os.path.isfile(uri):
                return uri

            raise Exception(f'Nie można odnaleźć pliku: {uri}')

        pisa_status = pisa.CreatePDF(html_string, dest=response, link_callback=link_callback)
        if pisa_status.err:
            return HttpResponse(f'Błąd podczas generowania PDF:<pre>{html_string}</pre>')

        return response

    return render(request, 'admin/admin_print_form.html', {
        'fieldsets': fieldsets,
        'default_selected': default_selected,
        'custom_filter_fields': custom_filter_fields,
        'model_name': model_name,
        'objects': objects,
        'model_verbose': model._meta.verbose_name,
    })


class PDFGenerateDirectly(TemplateView):
    """Generic view to directly generate PDF by xhtml2pdf library."""

    @staticmethod
    def link_callback(uri, rel, *args):
        """
        Przetwarza ścieżki URI w HTML na ścieżki systemowe,
        aby xhtml2pdf mógł załadować pliki (czcionki, obrazy, css).
        """
        # Ścieżka do plików statycznych (np. czcionki, css, obrazy)
        if uri.startswith(settings.STATIC_URL):
            path = finders.find(uri.replace(settings.STATIC_URL, ""))
            if path:
                return path

        # Ścieżka do plików mediów (np. uploady)
        if uri.startswith(settings.MEDIA_URL):
            path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
            if os.path.isfile(path):
                return path

        # Jeśli uri jest ścieżką absolutną i plik istnieje
        if os.path.isfile(uri):
            return uri

        raise Exception(f"Nie można odnaleźć pliku: {uri}")

    filename = 'ep_medbay.pdf'

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data(*args, **kwargs))

    def post(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data(*args, **kwargs))

    def render_to_response(self, context, **response_kwargs):
        # create pdf_preparation/pdf_SOME_preparation_template.html to render PDF
        pdf_name = context['model_name'].lower()
        self.template_name = f"pdf_preparation/pdf_{pdf_name}_preparation_template.html"

        html_string = render_to_string(self.template_name, context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{self.filename}"'
        pisa_status = pisa.CreatePDF(html_string, dest=response, link_callback=self.link_callback)
        if pisa_status.err:
            return HttpResponse(f'We had some errors <pre>{html_string}</pre>')
        return response

    def get_context_data(self, *args, **kwargs):
        context = super(PDFGenerateDirectly, self).get_context_data(*args, **kwargs)

        model_name = self.request.GET.get('model') or self.request.POST.get('model')
        ids_str = self.request.GET.get('ids')
        if ids_str and model_name != 'inspection_plan_table':
            ids = [int(id) for id in ids_str.split(",")]

            if model_name == 'passport':
                devices = Device.objects.filter(pk__in=ids)
                context['devices'] = devices
                self.filename = 'paszport.pdf'

            if model_name == 'device':
                device = Device.objects.filter(pk__in=ids).first()
                context['device'] = device
                context['request'] = self.request
                self.filename = 'urzadzenie.pdf'

            if model_name == 'service':
                service = Service.objects.filter(pk__in=ids)
                context['service'] = service
                self.filename = 'zlecenie.pdf'

            if model_name == 'all_table':
                context['now'] = datetime.datetime.now()
                devices = Device.objects.filter(pk__in=ids).order_by("pk")
                context['devices'] = devices

            context['ids'] = ids_str

            if model_name == 'inspection_plan_table':
                context['now'] = datetime.datetime.now()
                titles = self.request.POST.get('titles').split(',')
                ids_str = self.request.POST.get('ids')
                if titles:
                    titles = [title.strip() for title in titles if title]
                    context['titles'] = titles
                context['ids'] = [id.replace("<SEP>", "").split(",")[1:] for id in ids_str.split(",<SEP>,")]

        context['model_name'] = model_name

        return context

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(PDFGenerateDirectly, self).dispatch(*args, **kwargs)



class PDFGenerate(TemplateView):
    """Generic view to generate PDF by xhtml2pdf library."""

    template_name = 'pdf_generate_template.html'
    filename = 'ep_medbay.pdf'
    cmd_options = {
        'orientation': 'portrait',
    }

    @staticmethod
    def link_callback(uri, rel, *args):
        """
        Przetwarza ścieżki URI w HTML na ścieżki systemowe,
        aby xhtml2pdf mógł załadować pliki (czcionki, obrazy, css).
        """
        # Ścieżka do plików statycznych (np. czcionki, css, obrazy)
        if uri.startswith(settings.STATIC_URL):
            path = finders.find(uri.replace(settings.STATIC_URL, ""))
            if path:
                return path

        # Ścieżka do plików mediów (np. uploady)
        if uri.startswith(settings.MEDIA_URL):
            path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
            if os.path.isfile(path):
                return path

        # Jeśli uri jest ścieżką absolutną i plik istnieje
        if os.path.isfile(uri):
            return uri

        raise Exception(f"Nie można odnaleźć pliku: {uri}")
    def get_service_description(self, obj):
        """
        Returns service description based on status
        """
        now = datetime.datetime.now()

        if obj.status == 1:
            description = "Zapytanie ofertowe do zlecenia "
        elif obj.status == 2:
            description = "Akceptacja oferty do zlecenia "
        else:
            description = "Zlecenie "

        contractor = None

        if obj.contractor and obj.sort == 1:
            contractor = obj.contractor

        if obj.person_completing and obj.sort == 0:
            contractor = obj.person_completing

        description += u'nr #%s do zgłoszenia nr #%s wysłane %s do %s' % \
                       (obj.pk, obj.ticket.all().id, now.strftime("%d_%m_%Y_o_godz._%H_%M"), contractor)

        return description

    def post(self, *args, **kwargs):
        return self.render(self.get_context_data(**kwargs))

    def render(self, context, **response_kwargs):
        """
        Override function render to add comments, add pdf to model Document and sending mail.
        Return redirect.
        """
        # TODO: refactor this function. I'm serious.
        now = datetime.datetime.now()
        model_name = self.request.POST.get('model')

        ids = self.request.POST.get('ids')
        if ids and ids.lower() != 'none':
            try:
                ids_list = [int(i) for i in ids.split(",")]
            except ValueError:
                ids_list = []
        else:
            ids_list = []

        if model_name == 'Passport':
            self.filename = 'paszport.pdf'

        pdf_file = self.generate_pdf(context)

        user = User.objects.get(pk=self.request.user.pk)

        if model_name == 'Passport':
            return pdf_file

        model = import_string("cmms.models.{}".format(model_name))

        try:
            content_type_from_model_name = ContentType.objects.get(model=model_name.lower(), app_label="cmms")

            if model_name == 'Service':
                content_type_ticket = ContentType.objects.get(model='ticket', app_label="cmms")

        except ContentType.DoesNotExist:
            raise Http404

        if model:
            objs = model.objects.filter(pk__in=ids)
            for obj in objs:
                if model_name == "Service":
                    if obj.status == 1:
                        document_sort = 10
                        self.filename = f"Zapytanie_ofertowe_do_Zlecenia_nr_#{obj.pk}.pdf"
                    elif obj.status == 2:
                        document_sort = 11
                        self.filename = f"Akceptacja_oferty_do_Zlecenia_nr_#{obj.pk}.pdf"
                    else:
                        document_sort = 4
                        self.filename = f"Zlecenie_nr_#{obj.pk}_{obj.ticket.all().id}.pdf"

                    description = self.get_service_description(obj)
                    document = Document(
                        name=self.filename,
                        description=description,
                        sort=document_sort,
                        timestamp=now,
                        date_document=now,
                        contractor=obj.contractor,
                        person_adding=user,
                    )
                    document.save()
                    document.scan.save(self.filename, ContentFile(pdf_file.content))
                    document.service.add(obj)
                    for ticket in obj.ticket.all():
                        document.ticket.add(ticket)
                    for device in ticket.device.all():
                        document.device.add(device)

                    if "send-pdf" in self.request.POST:
                        # execute task
                        send_service_email.delay(user.pk, obj.id, document.id, content_type_from_model_name.id,
                                                 content_type_ticket.id)
                    else:
                        if obj.status == 1:
                            comment_text = f"Zapisano zapytanie ofertowe do zlecenia nr #{obj.pk}."
                        elif obj.status == 2:
                            comment_text = f"Zapisano akceptację oferty do zlecenia nr #{obj.pk}."
                        else:
                            comment_text = f"Zapisano zlecenie nr #{obj.pk}."

                        comment = mark_safe(comment_text)

                        Comment.objects.create(
                            comment=comment,
                            site_id=1,
                            object_pk=obj.pk,
                            content_type_id=content_type_from_model_name.id,
                            user_id=user.id,
                            submit_date=now
                        )

                        for ticket in obj.ticket.all():
                            Comment.objects.create(
                                comment=comment,
                                site_id=1,
                                object_pk=ticket.pk,
                                content_type_id=content_type_ticket.id,
                                user_id=user.id,
                                submit_date=now
                            )

        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect("/serwis")

    def get_context_data(self, **kwargs):
        context = super(PDFGenerate, self).get_context_data(**kwargs)

        ids = self.request.POST.get('ids') or self.request.GET.get('ids')
        if ids and ids.lower() != 'none':
            try:
                ids_list = [int(i) for i in ids.split(",")]
            except ValueError:
                ids_list = []
        else:
            ids_list = []

        context['ids'] = ids_list
        # dalsza logika...

        return context

    def generate_pdf(self, context):
        """Generate PDF file using xhtml2pdf"""

        template_path = self.template_name
        response = HttpResponse(content_type='application/pdf')

        # find the template and render it.
        template = get_template(template_path)
        html = template.render(context)

        # create a pdf
        pisa_status = pisa.CreatePDF(
            html, dest=response, link_callback=self.link_callback)

        # if error then show some funy view
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')

        return response



class PDFPreview(TemplateView):
    """Create preview PDF based on given model. PDF created for one object."""

    template_name = 'pdf_preview_template.html'

    @staticmethod
    def link_callback(uri, rel, *args):
        """
        Przetwarza ścieżki URI w HTML na ścieżki systemowe,
        aby xhtml2pdf mógł załadować pliki (czcionki, obrazy, css).
        """
        # Ścieżka do plików statycznych (np. czcionki, css, obrazy)
        if uri.startswith(settings.STATIC_URL):
            path = finders.find(uri.replace(settings.STATIC_URL, ""))
            if path:
                return path

        # Ścieżka do plików mediów (np. uploady)
        if uri.startswith(settings.MEDIA_URL):
            path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
            if os.path.isfile(path):
                return path

        # Jeśli uri jest ścieżką absolutną i plik istnieje
        if os.path.isfile(uri):
            return uri

        raise Exception(f"Nie można odnaleźć pliku: {uri}")

    def show_send_button(self):
        model = self.request.GET.get("model")
        ids_str = self.request.GET.get("id")
        if ids_str:
            ids = [int(id) for id in ids_str.split(",")]

        if model == 'Service':
            service = Service.objects.get(pk=ids)
            if service.sort == 1 and service.contractor:
                return True
            elif service.sort == 0 and service.person_completing:
                return True

        return False

    def get_context_data(self, **kwargs):
        context = super(PDFPreview, self).get_context_data(**kwargs)
        now = datetime.datetime.now()

        model = self.request.GET.get("model")
        ids_str = self.request.GET.get("id")
        if ids_str:
            ids = [int(id) for id in ids_str.split(",")]

        if model == 'Service':
            context_data = {"now": now.strftime("%d.%m.%Y")}

            service = Service.objects.get(pk=ids)
            context_data['service'] = service

            tickets = service.ticket.all()
            devices = Device.objects.filter(ticket__in=tickets).distinct()
            context_data['devices'] = devices

            from crm.models import Location, UserProfile
            locations = Location.objects.filter(device__in=devices).distinct()
            context_data['locations'] = locations

            responsible_pks = []
            for i in devices:
                try:
                    ts_pk = i.technical_supervisor.pk
                except:
                    ts_pk = None

                if ts_pk and ts_pk not in responsible_pks:
                    responsible_pks += [ts_pk, ]

            responsible = UserProfile.objects.filter(pk__in=responsible_pks).distinct()
            context_data['responsible'] = responsible

            context_data['request'] = self.request

            if service.status == 1:
                preparation_template = 'documents/service_deal.html'
            elif service.status == 2:
                preparation_template = 'documents/service_deal_acceptance.html'
            else:
                preparation_template = 'documents/service_other_documents.html'

            # render PDF
            rendered_template = render_to_string(preparation_template, context_data)

        if model == 'Passport':
            devices = Device.objects.filter(pk__in=ids)
            passport_entries = {}

            # create pdf_preparation/pdf_SOME_preparation_template.html to render PDF
            preparation_template = "pdf_preparation/pdf_passport_preparation_template.html"
            rendered_template = render_to_string(preparation_template, {"devices": devices,
                                                                        "passport_entries": passport_entries,
                                                                        "now": now.strftime("%d.%m.%Y")})

        #context['pdf_form'] = PDFForm(initial={'body_pdf': rendered_template})
        context['model'] = model
        context['ids'] = ids_str

        return context

    def generate_pdf(self, html_content):
        """Generate PDF file using xhtml2pdf"""

        response = HttpResponse(content_type='application/pdf')

        # create a pdf
        pisa_status = pisa.CreatePDF(
            html_content, dest=response, link_callback=self.link_callback)

        # if error then show some funy view
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html_content + '</pre>')

        return response



class GenerateXLSPreview(TemplateView):
    """Create list of columns given model to select for export."""

    template_name = 'xls_preview_template.html'

    def post(self, request, *args, **kwargs):
        return self.render(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(GenerateXLSPreview, self).get_context_data(**kwargs)

        model = self.request.GET.get('model') or self.request.POST.get('model')
        if model:
            context['model'] = model
            if model == 'InspectionPlan':
                rows = self.request.POST.getlist('ids[]')
                titles = self.request.POST.getlist('titles[]')
                context['rows'] = rows
                context['titles'] = titles
                context['columns'] = titles
            else:
                model_obj = import_string(f"cmms.models.{model}")
                model_fields = model_obj._meta.fields
                if model == 'Device':
                    context['model_fields'] = [
                        {
                            "name": x.name,
                            "verbose_name": x.verbose_name
                        } for x in model_fields
                        if x.name not in [
                            "service_interval",
                            "service_interval_type",
                        ]
                    ]
                else:
                    context['model_fields'] = model_fields

            ids = self.request.GET.get('ids')
            if ids:
                context['ids'] = ids

        return context

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(GenerateXLSPreview, self).dispatch(*args, **kwargs)



def render_xls(model_str, objs, exported_columns=None):
    """Function rendering xls. Uses xlwt library."""

    now = datetime.datetime.now()
    wb = Workbook()
    ws = wb.add_sheet('Exported %ss' % model_str)
    response = HttpResponse(content_type="application/vnd.ms-excel")
    response['Content-Disposition'] = 'attachment; filename=exported_%ss_%s_%s.xls' \
                                      % (model_str.lower(), now.date(), now.time().strftime("%H_%M"))

    row = 1
    for obj in objs:
        if not exported_columns:
            exported_columns = [field.name for field in obj._meta.fields]

        # obsluga customowych metod w modelu
        for field in exported_columns:
            # jak ktoś przypadkiem dziabnie funkcję zamiast stringa to olej
            if not isinstance(field, str):
                continue

            # get field properties for field
            field_props = get_field_properties(obj, field)

            description = field_props['verbose_name']
            item = field_props['value']

            # if it's the first row, write item verbose name
            if row == 1:
                ws.write(row - 1, exported_columns.index(field), description)

            # dopisz
            ws.write(row, exported_columns.index(field), item)

        row += 1
    wb.save(response)

    return response



def render_list_xls(model_str, rows, header):
    """Function rendering xls from list. Uses xlwt library."""

    now = datetime.datetime.now()
    wb = Workbook()
    ws = wb.add_sheet('Exported %ss' % model_str)
    response = HttpResponse(content_type="application/vnd.ms-excel")
    response['Content-Disposition'] = 'attachment; filename=exported_%ss_%s_%s.xls' \
                                      % (model_str.lower(), now.date(), now.time().strftime("%H_%M"))

    col = 0
    for title in header:
        ws.write(0, col, title)
        col += 1

    row = 1
    for element in rows:
        col = 0
        for title in header:
            ws.write(row, col, element[title])
            col += 1

        row += 1
    wb.save(response)

    return response



class GenerateXLS(TemplateView):
    """Generic view to generate XLS by xlwt library."""

    def post(self, request, *args, **kwargs):
        response = None
        model_str = self.request.POST.get('model')
        if model_str == 'InspectionPlan':
            rows_to_export = []
            all_cols = eval(self.request.POST['ids'])
            titles = eval(self.request.POST['titles'])
            titles = [title.strip() for title in titles]
            one_row = {}
            num_title_col = 0
            for col in all_cols:
                if col != '<SEP>':
                    title = titles[num_title_col]
                    one_row[title] = col
                    num_title_col += 1
                else:
                    rows_to_export.append(one_row)
                    one_row = {}
                    num_title_col = 0

            titles = [(title, title) for title in titles]
            response = render_list_xls(model_str, rows_to_export, titles)
        return response

    def get(self, request, *args, **kwargs):
        response = None
        model_str = self.request.GET.get('model')
        if model_str:
            model = import_string(f"cmms.models.{model_str}")
            ids = self.request.GET.get('ids')
            objs = model.objects.filter(id__in=ids.split(","))
            exported_columns = self.request.GET.getlist('exported_columns')

            response = render_xls(model_str, objs, exported_columns)

        return response

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(GenerateXLS, self).dispatch(*args, **kwargs)




# Create your views here.
