import datetime

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render
from django.template.defaultfilters import lower
from django.template.loader import render_to_string, get_template
from django.utils.decorators import method_decorator
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View
from django_comments.models import Comment
#from utils.forms import PDFForm
from xhtml2pdf import pisa
from xlwt import Workbook

from cmms.models import Service, Document, Device
from utils.logic import get_field_properties
from utils.tasks import send_service_email

User = get_user_model()


def print_admin(request, model_name):
    from dane import admin

    # try to get admin class for model_name
    try:
        model = ContentType.objects.get(model=model_name.lower()).model_class()
        admin_object = admin.dane_admin._registry[model]
    except:
        raise Http404()

    # get object
    object_pks = request.GET.get("objects").split(",")
    objects = []

    for object_pk in object_pks:
        try:
            obj = model.objects.get(pk=int(object_pk))
        except:
            raise Http404()
        objects.append(obj)

    # try to get list of options from admin
    try:
        fieldsets = admin_object.get_printed_fieldsets(request, obj)
    except:
        # default to all fieldsets from admin + inlines
        # get original fieldsets
        original_fieldsets = admin_object.get_fieldsets(request, obj)

        # convert original fieldsets to something like: [ (fieldset_name, [(field,verbose), (field, verbose),],), ]
        fieldsets = []
        for fieldset in original_fieldsets:
            # get fieldset name
            fieldset_name = fieldset

            # create empty list
            fieldset_fields = []
            for field in fieldset['fields']:
                try:
                    # assume it's a field, not a function and get field object and then it's verbose name
                    _field = obj._meta.get_field(field)
                    verbose = f"{str(_field.verbose_name)}"
                except:
                    try:
                        verbose = getattr(obj, field).short_description
                    except:
                        verbose = fieldset_name

                # merge field and it's verbose name into tuple and append
                fieldset_fields.append((field, verbose))

            # merge into tuple and append
            fieldsets.append((fieldset_name, fieldset_fields))

        # support inlines
        inlines = admin_object.get_inline_instances(request)

        # try to get inline excludes
        try:
            excluded_inlines = admin_object.excluded_inlines
        except:
            excluded_inlines = []

        for instance in inlines:
            if instance.model.__name__ not in excluded_inlines:
                fieldsets.append((instance.verbose_name, [(f"inline_{instance.model.__name__}", instance.verbose_name)]))

        # comments block
        if model_name == "ticket" or model_name == "service":
            fieldsets.append(("Komentarze", [("comments", "Komentarze")]))

        # inline history
        try:
            if admin_object.show_history:
                fieldsets.append(("Historia", [("history", "Historia zmian")]))
        except:
            pass

    try:
        default_selected = admin_object.get_default_selected(request, obj)
    except:
        default_selected = []

    try:
        custom_filter_fields = admin_object.custom_filter_fields
    except:
        custom_filter_fields = []

    if request.method == 'POST':
        # convert request QueryDict to regular dictionary
        request_data = dict(request.POST.lists())

        # assume we shouldn't show comments unless stated otherwise
        show_comments = False

        # assume we shouldn't show history unless stated otherwise
        show_history = False

        # assume we shouldn't show external services unless stated otherwise
        show_external_services = False

        # assume we shouldn't show invoice summary unless stated otherwise
        show_invoice_summary = False

        # stupid hack
        show_costbreakdown = False

        inlines = []

        selected_fieldsets = {}
        # get all fields for fieldsets
        for key in request_data.keys():
            if key.startswith("fields_"):
                if key[7:] == "Komentarze":
                    if "comments" in request_data[key]:
                        show_comments = True
                elif key[7:] == "Historia":
                    if "history" in request_data[key]:
                        show_history = True
                elif key[7:] == "Zlecenia" and model_name == "invoice":
                    if "external_service" in request_data[key]:
                        show_external_services = True
                elif key[7:] == "Podsumowanie" and model_name == "invoice":
                    if "invoice_summary" in request_data[key]:
                        show_invoice_summary = True
                else:
                    inlines += [x[7:] for x in request_data[key] if x.startswith("inline_")]
                    fields = [x for x in request_data[key] if not x.startswith("inline_")]
                    selected_fieldsets[key[7:]] = {"fields": tuple(fields)}

                    if "inline_CostBreakdown" in request_data[key]:
                        show_costbreakdown = True

        rendered = []

        for obj in objects:
            # simulate getting form
            request.method = 'GET'

            # get change_view
            response = admin_object.change_view(request, str(obj.pk))

            # make it use custom template
            response.template_name = 'admin/dane/pdf_change_form.html'

            # make all fields readonly
            try:
                response.context_data['adminform'].readonly_fields += tuple(
                    response.context_data['adminform'].form.fields.keys())
            except:
                response.context_data['adminform'].readonly_fields = response.context_data['adminform']

            # make sure we're outputting it in the right order
            new_fieldsets = []
            for fieldset in response.context_data['adminform'].fieldsets:
                # get name
                name = fieldset
                # check if it's already in fieldset names
                if selected_fieldsets.get(name):
                    new_fieldsets.append((name, selected_fieldsets[name]))

            response.context_data['adminform'].fieldsets = new_fieldsets

            # make all inlines readonly
            for formset in response.context_data['inline_admin_formsets']:
                formset.readonly_fields = formset.fieldsets['fields']
                formset.formset.can_delete = False
                formset.formset.can_add = False
                formset.formset.hide_scan = True
                formset.original = False
                # make sure extra forms are removed
                for i in range(0, formset.formset.extra):
                    try:
                        del formset.formset.forms[-1]
                    except:
                        # uhm, this is not supposed to happen
                        pass

                if formset.formset.model._meta.model_name == "costbreakdown" and not show_costbreakdown:
                    response.context_data['inline_admin_formsets'].remove(formset)

            # copy our custom context data to response
            response.context_data['show_comments'] = show_comments
            response.context_data['show_external_services'] = show_external_services
            response.context_data['show_invoice_summary'] = show_invoice_summary
            response.context_data['model_verbose'] = model._meta.verbose_name

            # remove inlines that are not enabled
            for index, inline in enumerate(response.context_data['inline_admin_formsets']):
                if inline.opts.model.__name__ not in inlines:
                    del response.context_data['inline_admin_formsets'][index]

            # render
            response.render()

            # create absolute path for images
            absolute_path = f"{request.META.get('HTTP_ORIGIN')}/site_media"

            # replace /site_media with absolute path in rendered content
            content = response.rendered_content.replace('/site_media', absolute_path)

            # mark it as safe for Django not to escape characters in HTML code
            content = mark_safe(content)

            # append to the list of rendered objects
            rendered.append(content)

        # convert to pdf
        html_string = render_to_string('pdf_preparation/pdf_admin_wrapper.html', {'rendered': rendered})
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="document.pdf"'
        pisa_status = pisa.CreatePDF(html_string, dest=response)
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html_string + '</pre>')
        return response

    return render(request, 'admin/admin_print_form.html', locals())


class PDFGenerateDirectly(TemplateView):
    """Generic view to directly generate PDF by xhtml2pdf library."""

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
        pisa_status = pisa.CreatePDF(html_string, dest=response)
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
                device = Device.objects.filter(pk__in=ids)
                context['device'] = device
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



class PDFGenerate(View):
    """Generic view to generate PDF by xhtml2pdf library."""

    template_name = 'pdf_generate_template.html'
    filename = 'ep_medbay.pdf'
    cmd_options = {
        'orientation': 'portrait',
    }

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
        if ids:
            ids = [int(id) for id in ids.split(",")]

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
        """Generate PDF from edited text by CKEditor. Return context."""

        context = super(PDFGenerate, self).get_context_data(**kwargs)

        body_pdf = self.request.POST.get('body_pdf')

        if body_pdf:
            context['body_pdf'] = mark_safe(body_pdf)

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
            html, dest=response)

        # if error then show some funy view
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')

        return response



class PDFPreview(TemplateView):
    """Create preview PDF based on given model. PDF created for one object."""

    template_name = 'pdf_preview_template.html'

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
            html_content, dest=response)

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
