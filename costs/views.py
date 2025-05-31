from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseNotAllowed
from django.views.generic import ListView, TemplateView, View
from django.contrib import messages
from cmms.models import Device
from costs.forms import CostRangeForm
from crm.cost_breakdown_creator import CostBreakdownCreator
from crm.models import Invoice, CostBreakdown


class ResetCostBreakdown(View):

    def get(self, request, *args, **kwargs):
        invoice_id = request.GET.get('invoice')

        if invoice_id:
            try:
                invoice_obj = Invoice.objects.get(pk=int(invoice_id))
            except Invoice.DoesNotExist:
                return HttpResponse('Invoice not found', status=404)

            CostBreakdown.objects.filter(invoice=int(invoice_id)).delete()
            failed_devices = CostBreakdownCreator(invoice_obj).breakdown_costs()

            try:
                content_type = ContentType.objects.get(model='invoice')
                LogEntry.objects.create(
                    content_type=content_type,
                    object_id=int(invoice_id),
                    change_message='Zresetowano podział kosztów',
                    user=request.user,
                    action_flag=2,
                )
            except ContentType.DoesNotExist:
                pass

            # push warnings for every device that has no cost center
            for device_id in failed_devices:
                try:
                    device = Device.objects.get(pk=device_id)
                    messages.warning(
                        request,
                        f'Urządzenie "{device}" nie jest przypisane do żadnego centrum kosztowego.'
                    )
                except Device.DoesNotExist:
                    pass

            messages.info(request, 'Zresetowano podział kosztów.')
            return HttpResponse('reset')

        return HttpResponseNotAllowed(['GET'])


class CostsView(ListView):
    template_name = "costs/costs.html"
    context_object_name = 'devices'
    model = Device


class CostsRangeView(TemplateView):
    template_name = 'costs/costs_range.html'
    form_class = CostRangeForm

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        device_id = request.GET.get('device_id')
        form = self.form_class()
        form.fields['device_id'].initial = device_id

        context['form'] = form
        if device_id:
            try:
                device = Device.objects.get(id=device_id)
                context['device'] = device
            except Device.DoesNotExist:
                context['device'] = None

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        device_id = request.GET.get('device_id')
        form = self.form_class(request.POST)
        form.fields['device_id'].initial = device_id

        context['form'] = form

        if device_id:
            try:
                device = Device.objects.get(id=device_id)
                context['device'] = device
            except Device.DoesNotExist:
                context['device'] = None

        if form.is_valid():
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')

            context['net_cost'] = 0.00
            context['gross_cost'] = 0.00

            if start_date and end_date and device_id:
                invoices = Invoice.objects.filter(posting_date__range=[start_date, end_date])
                invoice_ids = invoices.values_list('id', flat=True)
                costs = CostBreakdown.objects.filter(
                    invoice__in=invoice_ids,
                    device_id=device_id
                ).aggregate(net_cost_sum=Sum('net_cost'), gross_cost_sum=Sum('gross_cost'))

                net_cost_sum = costs.get('net_cost_sum')
                gross_cost_sum = costs.get('gross_cost_sum')

                context['net_cost'] = round(net_cost_sum, 2) if net_cost_sum is not None else 0.00
                context['gross_cost'] = round(gross_cost_sum, 2) if gross_cost_sum is not None else 0.00

        return self.render_to_response(context)