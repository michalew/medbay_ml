# -*- coding: utf-8 -*-
from decimal import Decimal

from django import forms
from django.forms.models import BaseInlineFormSet
from cmms.models import Service, Ticket, Device, Document, Mileage, DevicePassport
from crm.models import Contractor, Invoice, CHOICES_INVOICE_STATUS, Hospital, InvoiceItem, CostBreakdown
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper, FilteredSelectMultiple
from .admin_widgets import SecuredAdminFileWidget

DATE_OPTION = (
    (0, u"Wszystkie"),
    (1, u"jest równa"),
    (2, u"jest większa równa"),
    (3, u"jest mniejsza równa"),
    (4, u"jest większa"),
    (5, u"jest mniejsza"),
    (6, u"jest pomiędzy"),
    (7, u"ostatnie 7 dni"),
)

BASE_OPTION = (
    (0, u"Wszystkie"),
    (1, u"jest równy"),
    (2, u"nie jest równy"),
)

WIDGET_OPTION = (
    (0, u"Wszystkie"),
    (1, u"zawiera jedno z"),
    (2, u"nie zawiera"),
)

TEXT_OPTION = (
    (0, u"Wszystkie"),
    (1, u"zawiera"),
    (2, u"nie zawiera"),
)

NUMBER_OPTION = (
    (0, u"Wszystkie"),
    (1, u"jest równa"),
    (2, u"jest większa równa"),
    (3, u"jest mniejsza równa"),
    (4, u"jest większa"),
    (5, u"jest mniejsza"),
)


class AdvancedMileageFilter(forms.ModelForm):

    advanced_mileage_filter = forms.BooleanField(widget=forms.HiddenInput)
    device = forms.CharField(
        label=u"Urządzenia", required=False, widget=forms.HiddenInput)
    device_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)

    #ticket = forms.CharField(label=u"Zgłoszenia", required=False, widget=forms.HiddenInput)
    #ticket_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)

    date = forms.CharField(label=u"Data utworzenia",  required=False)
    date_from = forms.CharField(label=u"Data dodania",  required=False)
    date_to = forms.CharField(required=False)
    date_operator = forms.ChoiceField(choices=DATE_OPTION, required=False)

    status_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)

    unit_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)

    #hospital_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    #sort_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    #person_assigned_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    #description_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)
    #status_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    #person_creating_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    #contractor = forms.CharField(label=u"Firma serwisująca", required=False)
    #contractor_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    #person_completing_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    #comment = forms.CharField(label=u"Komentarz", widget=forms.Textarea, required=False)
    #comment_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)

    class Meta:
        model = Mileage
        exclude = []

    def __init__(self, *args, **kwargs):
        super(AdvancedMileageFilter, self).__init__(*args, **kwargs)
        self.fields['advanced_mileage_filter'].initial = True


class AdvancedServiceFilter(forms.ModelForm):

    advanced_service_filter = forms.BooleanField(widget=forms.HiddenInput)
    ticket = forms.CharField(
        label=u"Zgłoszenia", required=False, widget=forms.HiddenInput)
    ticket_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)
    date_add = forms.CharField(label=u"Data dodania",  required=False)
    date_add_from = forms.CharField(label=u"Data dodania",  required=False)
    date_add_to = forms.CharField(required=False)
    date_add_operator = forms.ChoiceField(choices=DATE_OPTION, required=False)
    hospital_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    sort_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    person_assigned_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    description_operator = forms.ChoiceField(
        choices=TEXT_OPTION, required=False)
    status_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    person_creating_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    contractor = forms.CharField(label=u"Firma serwisująca", required=False)
    contractor_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    person_completing_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    comment = forms.CharField(
        label=u"Komentarz", widget=forms.Textarea, required=False)
    comment_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)

    class Meta:
        model = Service
        exclude = []

    def __init__(self, *args, **kwargs):
        super(AdvancedServiceFilter, self).__init__(*args, **kwargs)
        self.fields['advanced_service_filter'].initial = True


class AdvancedTicketFilter(forms.ModelForm):

    advanced_ticket_filter = forms.BooleanField(widget=forms.HiddenInput)
    device = forms.CharField(
        label=u"Urządzenia", required=False, widget=forms.HiddenInput)
    device_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)
    date_add = forms.CharField(label=u"Data dodania",  required=False)
    date_add_from = forms.CharField(label=u"Data dodania",  required=False)
    date_add_to = forms.CharField(required=False)
    date_add_operator = forms.ChoiceField(choices=DATE_OPTION, required=False)
    sort_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    cyclic_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    description_operator = forms.ChoiceField(
        choices=TEXT_OPTION, required=False)
    status_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    person_creating_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    person_closing_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    date_closing_operator = forms.ChoiceField(
        choices=DATE_OPTION, required=False)
    date_closing_from = forms.CharField(
        label=u"Data zamknięcia", required=False)
    date_closing_to = forms.CharField(required=False)
    priority_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    cost_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    comment = forms.CharField(
        label=u"Komentarz", widget=forms.Textarea, required=False)
    comment_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)

    class Meta:
        model = Ticket
        exclude = []

    def __init__(self, *args, **kwargs):
        super(AdvancedTicketFilter, self).__init__(*args, **kwargs)
        self.fields['advanced_ticket_filter'].initial = True


class AdvancedInvoiceFilter(forms.ModelForm):
    advanced_invoice_filter = forms.BooleanField(widget=forms.HiddenInput)
    name = forms.CharField(widget=forms.TextInput,
                           label=u'Nazwa', required=False)
    name_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)
    number = forms.CharField(widget=forms.TextInput, label=u'Numer')
    number_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)
    date = forms.CharField(label=u'Data', required=False)
    date_from = forms.CharField(required=False)
    date_to = forms.CharField(required=False)
    date_operator = forms.ChoiceField(choices=DATE_OPTION, required=False)
    net_value = forms.CharField(label=u'Suma netto', required=False)
    net_value_operator = forms.ChoiceField(
        choices=NUMBER_OPTION, required=False)
    gross_value = forms.CharField(label=u'Suma brutto', required=False)
    gross_value_operator = forms.ChoiceField(
        choices=NUMBER_OPTION, required=False)
    status = forms.ChoiceField(
        choices=CHOICES_INVOICE_STATUS, label=u'Status', required=False)
    status_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    contractor = forms.CharField(label=u"Kontrahent", required=False)
    contractor_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    hospital = forms.CharField(label=u'Szpital', required=False)
    hospital_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    service = forms.CharField(
        label=u"Zlecenie", required=False, widget=forms.HiddenInput)
    service_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)
    ticket = forms.CharField(
        label=u"Zgłoszenie", required=False, widget=forms.HiddenInput)
    ticket_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)
    device = forms.CharField(
        label=u"Urządzenie", required=False, widget=forms.HiddenInput)
    device_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)

    class Meta:
        model = Invoice
        exclude = []


class AdvancedDeviceFilter(forms.ModelForm):

    advanced_device_filter = forms.BooleanField(widget=forms.HiddenInput)
    name_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)
    genre = forms.CharField(label=u"Rodzaj", required=False)
    genre_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    make = forms.CharField(label=u"Producent", required=False)
    make_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    model_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)
    serial_number_operator = forms.ChoiceField(
        choices=TEXT_OPTION, required=False)
    inventory_number_operator = forms.ChoiceField(
        choices=TEXT_OPTION, required=False)
    udt_number_operator = forms.ChoiceField(
        choices=TEXT_OPTION, required=False)
    group_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    cost_centre = forms.CharField(label=u"Centrum Kosztowe", required=False)
    cost_centre_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    location_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    location_place_operator = forms.ChoiceField(
        choices=TEXT_OPTION, required=False)
    date_manufactured_operator = forms.ChoiceField(
        choices=DATE_OPTION, required=False)
    date_manufactured_from = forms.CharField(
        label=u"Data produkcji", required=False)
    date_manufactured_to = forms.CharField(required=False)
    date_bought_operator = forms.ChoiceField(
        choices=DATE_OPTION, required=False)
    date_bought_from = forms.CharField(label=u"Data zakupu", required=False)
    date_bought_to = forms.CharField(required=False)
    date_warranty_operator = forms.ChoiceField(
        choices=DATE_OPTION, required=False)
    date_warranty_from = forms.CharField(
        label=u"Data upływu gwarancji", required=False)
    date_warranty_to = forms.CharField(required=False)
    remarks_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)
    person_responsible_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    technical_supervisor_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    status_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    contractor = forms.CharField(label=u"Firma serwisująca", required=False)
    contractor_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)

    class Meta:
        model = Device
        exclude = []

    def __init__(self, *args, **kwargs):
        super(AdvancedDeviceFilter, self).__init__(*args, **kwargs)
        self.fields['advanced_device_filter'].initial = True
        self.fields['status'].initial = ""
        self.fields['group'].initial = ""


class AdvancedDocumentFilter(forms.ModelForm):

    advanced_document_filter = forms.BooleanField(widget=forms.HiddenInput)
    name_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)
    device = forms.CharField(
        label=u"Urządzenie", required=False, widget=forms.HiddenInput)
    device_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)
    ticket = forms.CharField(
        label=u"Zgłoszenie", required=False, widget=forms.HiddenInput)
    ticket_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)
    service = forms.CharField(
        label=u"Zlecenie", required=False, widget=forms.HiddenInput)
    service_operator = forms.ChoiceField(choices=WIDGET_OPTION, required=False)
    description_operator = forms.ChoiceField(
        choices=TEXT_OPTION, required=False)
    sort_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    date_add = forms.CharField(label=u"Data dodania",  required=False)
    date_add_from = forms.CharField(label=u"Data dodania",  required=False)
    date_add_to = forms.CharField(required=False)
    date_add_operator = forms.ChoiceField(choices=DATE_OPTION, required=False)
    date_document_operator = forms.ChoiceField(
        choices=DATE_OPTION, required=False)
    date_document_from = forms.CharField(
        label=u"Data dokumentu", required=False)
    date_document_to = forms.CharField(required=False)

    date_expiration_operator = forms.ChoiceField(
        choices=DATE_OPTION, required=False)
    date_expiration_from = forms.CharField(
        label=u"Data ważności dokumentu", required=False)
    date_expiration_to = forms.CharField(required=False)
    number_operator = forms.ChoiceField(choices=TEXT_OPTION, required=False)
    person_adding_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    access_operator = forms.ChoiceField(choices=BASE_OPTION, required=False)
    contractor_operator = forms.ChoiceField(
        choices=BASE_OPTION, required=False)
    contractor = forms.CharField(label=u"Kontrahent", required=False)

    class Meta:
        model = Document
        exclude = []

    def __init__(self, *args, **kwargs):
        super(AdvancedDocumentFilter, self).__init__(*args, **kwargs)
        self.fields['advanced_document_filter'].initial = True


class TicketAdminForm(forms.ModelForm):
    def clean(self):
        if self.instance:
            status = self.instance.status

            if status == 2 and not self.current_user.is_superuser:
                raise forms.ValidationError(
                    u"Nie można zmieniać zgłoszeń o statusie ZAMKNIĘTE")

        if not self.instance.pk:
            # set person_creating
            self.cleaned_data['person_creating'] = self.current_user

        return self.cleaned_data

    class Meta:
        model = Ticket
        exclude = []


class DevicePassportInlineForm(forms.ModelForm):
    is_service = forms.BooleanField(label=u"Przegląd", initial=False, 
                                    required=False)

    class Meta:
        model = DevicePassport
        fields = ("added_date", "content", "is_service", )

    def save(self, *args, **kwargs):
        is_service = self.cleaned_data.get("is_service", False)
        device = self.cleaned_data.get("device", None)

        result = super(DevicePassportInlineForm, self).save(*args, **kwargs)
        if device and is_service:
            device.date_service = self.cleaned_data.get("added_date", None)
            device.save()
        return result


class DocumentAdminForm(forms.ModelForm):
    class Meta:
        model = Document
        exclude = []

    def __init__(self, *args, **kwargs):
        super(DocumentAdminForm, self).__init__(*args, **kwargs)
        self.fields['scan'].widget = SecuredAdminFileWidget()

    def save(self, force_insert=False, force_update=False, commit=True):
        d = super(DocumentAdminForm, self).save(commit=False)
        if not d.person_adding:
            d.person_adding = self.current_user

        if commit:
            d.save()

        return d


class MileageAdminForm(forms.ModelForm):
    class meta:
        model = Mileage
        exclude = ["history"]

    def clean(self):
        if self.instance:
            old_state = self.instance.state
            new_state = self.cleaned_data.get('state')

            if old_state > new_state:
                raise forms.ValidationError(
                    u"Nowy stan licznika nie może być mniejszy od poprzedniego")

        return self.cleaned_data

    def save(self, force_insert=False, force_update=False, commit=True):
        m = super(MileageAdminForm, self).save(commit=False)
        if not m.person_creating:
            m.person_creating = self.current_user

        if commit:
            m.save()

        return m


class ServiceAdminForm(forms.ModelForm):
    def clean(self):
        if self.instance:
            status = self.instance.status

            if status == 5 and not self.current_user.is_superuser:
                raise forms.ValidationError(
                    u"Nie można zmieniać zleceń o statusie ZAMKNIĘTE.")

            sort = self.cleaned_data['sort']
            contractor = self.cleaned_data['contractor']
            person_completing = self.cleaned_data['person_completing']
            if sort == 0 and contractor:
                raise forms.ValidationError(
                    u"W przypadku zleceń wewnętrznych, pole 'Firma serwisująca' powinno być puste.")
            if sort == 1 and person_completing:
                raise forms.ValidationError(
                    u"W przypadku zleceń zewnętrznych, pole 'Odbiorca zlecenia' powinno być puste.")

        for ticket in self.cleaned_data.get("ticket", []):
            if not ticket.device.all():
                raise forms.ValidationError(
                    u"Nie można dodać zgłoszenia nie powiązanego z żadnym urządzeniem do zlecenia")

        return self.cleaned_data

    class Meta:
        model = Service
        exclude = []


class InvoiceItemAdminForm(forms.ModelForm):
    net_price = forms.DecimalField(
        label=u'Cena netto', localize=True, max_digits=9, decimal_places=2)
    net_cost = forms.DecimalField(
        label=u'Koszt netto', localize=True, max_digits=9, decimal_places=2)
    gross_cost = forms.DecimalField(
        label=u'Koszt brutto', localize=True, max_digits=9, decimal_places=2)

    class Meta:
        model = InvoiceItem
        exclude = []


class InvoiceItemFormSet(BaseInlineFormSet):
    def clean(self):
        has_invoice_item = False
        for data in self.cleaned_data:
            if data and not data.get('DELETE'):
                has_invoice_item = True
                break
        if not has_invoice_item:
            raise forms.ValidationError(
                u"Dodaj minimum jedną pozycję do faktury")

        return super(InvoiceItemFormSet, self).clean()


class InvoiceAdminForm(forms.ModelForm):

    net_value = forms.DecimalField(
        label=u'Wartość netto', localize=True, max_digits=9, decimal_places=2)
    gross_value = forms.DecimalField(
        label=u'Wartość brutto', localize=True, max_digits=9, decimal_places=2)
    external_service = forms.MultipleChoiceField(label=u'Zlecenia')
    hospital = forms.ModelChoiceField(
        queryset=Hospital.objects.all(), label=u'Szpital', required=False)
    contractor = forms.ModelChoiceField(
        queryset=Contractor.objects.all(), label=u'Kontrahent', required=False)

    class Meta:
        model = Invoice
        exclude = []

    def __init__(self, *args, **kwargs):
        super(InvoiceAdminForm, self).__init__(*args, **kwargs)

        self.fields['external_service'].choices = [
            (service.id, service.description) for service in Service.objects.all()]
        self.fields['net_value'].widget.attrs['readonly'] = True
        self.fields['gross_value'].widget.attrs['readonly'] = True
        self.fields['net_value'].required = False
        self.fields['gross_value'].required = False

        if self.instance.pk:
            contractor_id = Contractor.objects.filter(
                name=self.instance.contractor)
            if contractor_id:
                contractor_id = contractor_id[0].id
                self.initial['contractor'] = contractor_id
            hospital_id = Hospital.objects.filter(name=self.instance.hospital)
            if hospital_id:
                hospital_id = hospital_id[0].id
                self.initial['hospital'] = hospital_id

    def clean(self):
        cleaned_data = super(InvoiceAdminForm, self).clean()

        if self.instance.id:
            net_cost = Decimal('0')
            gross_cost = Decimal('0')
            net_invoice = Decimal('0')
            gross_invoice = Decimal('0')

            if self.costbreakdowninline.is_valid() and self.invoiceiteminline.is_valid():
                invoice = Invoice.objects.get(id=self.instance.id)
                if invoice.status == 4 and self.instance.status == 4 and not self.current_user.is_superuser:
                    raise forms.ValidationError(
                        u"Nie można edytować zaakceptowanej faktury")

                for cost_data in self.costbreakdowninline.cleaned_data:
                    if cost_data and not cost_data['DELETE']:
                        net_cost += cost_data.get('net_cost', 0)
                        gross_cost += cost_data.get('gross_cost', 0)

                has_cost_invoice = False
                self.invoice_item_was_changed = False
                for cost_invoice in self.invoiceiteminline.cleaned_data:
                    if cost_invoice and not cost_invoice['DELETE']:
                        has_cost_invoice = True
                        net_invoice += cost_invoice.get('net_cost', 0)
                        gross_invoice += cost_invoice.get('gross_cost', 0)

                    if cost_invoice.get('id') and (cost_invoice['DELETE'] or str(cost_invoice['id'].net_cost) != str(cost_invoice['net_cost']) or
                                                   str(cost_invoice['id'].gross_cost) != str(cost_invoice['gross_cost']) or
                                                   str(cost_invoice['id'].net_price) != str(cost_invoice['net_price']) or
                                                   str(cost_invoice['id'].amount) != str(cost_invoice['amount'])):
                        self.invoice_item_was_changed = True

                if not has_cost_invoice:
                    raise forms.ValidationError(
                        u"Dodaj minimum jedną pozycję do faktury")

                tolerance = Decimal('0.02')
                min_net_cost = (1 - tolerance) * net_cost
                max_net_cost = (1 + tolerance) * net_cost

                min_gross_cost = (1 - tolerance) * gross_cost
                max_gross_cost = (1 + tolerance) * gross_cost

                if not self.invoice_item_was_changed and (net_invoice < min_net_cost or net_invoice > max_net_cost or
                                                          gross_invoice < min_gross_cost or gross_invoice > max_gross_cost):
                    raise forms.ValidationError(u'Suma wartości netto i brutto z podziału kosztów musi '
                                                u'równać się sumie netto i brutto faktury')

                if net_invoice > gross_invoice:
                    raise forms.ValidationError(u'Cena netto faktury musi być niższa od ceny brutto. '
                                                u'Popraw wartości pozycji faktury!')
                cleaned_data['net_value'] = net_invoice
                cleaned_data['gross_value'] = gross_invoice
            else:
                raise forms.ValidationError(
                    u'Wystąpił błąd w podziale kosztów lub pozycji faktury.')

        return cleaned_data


class CostBreakdownForm(forms.ModelForm):
    net_cost = forms.DecimalField(
        label=u'Koszt netto', localize=True, max_digits=9, decimal_places=2)
    gross_cost = forms.DecimalField(
        label=u'Koszt brutto', localize=True, max_digits=9, decimal_places=2)

    class Meta:
        model = CostBreakdown
        exclude = []

    def __init__(self, *args, **kwargs):
        super(CostBreakdownForm, self).__init__(*args, **kwargs)
        self.fields['device_name'].widget.attrs['readonly'] = True
        self.fields['device_id'].widget.attrs['readonly'] = True
        self.fields['device_manufacturer'].widget.attrs['readonly'] = True
        self.fields['device_model'].widget.attrs['readonly'] = True
        self.fields['device_serial_number'].widget.attrs['readonly'] = True
        self.fields['device_inventory_number'].widget.attrs['readonly'] = True
        self.fields['cost_center_id'].widget.attrs['readonly'] = True
