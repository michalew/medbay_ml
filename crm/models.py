from django.db import models
import cmms
from django.conf import settings
from django.contrib.auth.models import AbstractUser

import utils
from utils.models import DiffedHistoricalRecords

CHOICES_INVOICE_STATUS = (
    (1, 'Projekt'),
    (2, 'Zapisana'),
    (3, 'Zaakceptowana'),
    (4, u'Zaksięgowana'),
)

CHOICES_VAT = (
    (1, '8%'),
    (2, '23%'),
    (3, 'zw'),
)

User = settings.AUTH_USER_MODEL


class UserProfile(AbstractUser):
    stamp = models.ImageField(upload_to='stamps/', null=True, blank=True, verbose_name=u'Pieczątka')
    signature = models.ImageField(upload_to='signatures/', null=True, blank=True, verbose_name=u'Podpis')
    phone = models.CharField("Telefon", max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['username', 'first_name', ]

    def __str__(self):
        # check if name is provided
        try:
            name = self.get_full_name()
        except:
            name = self.username

        if not name:
            name = self.username

        return name


# Create your models here.
class Hospital(models.Model):
    name = models.CharField(max_length=255, verbose_name=u'Nazwa')
    street = models.CharField(max_length=255, verbose_name=u'Ulica')
    street_number = models.CharField(max_length=255, verbose_name=u'Nr posesji')
    postal_code = models.CharField(max_length=255, verbose_name=u'Kod pocztowy')
    city = models.CharField(max_length=255, verbose_name=u'Miejscowość')
    logo = models.ImageField(upload_to='logo/', null=True, blank=True, verbose_name=u'Logo')
    NIP = models.BigIntegerField(verbose_name=u'NIP')
    REGON = models.BigIntegerField(verbose_name=u'REGON')
    KRS = models.BigIntegerField(verbose_name=u'KRS')
    telephone = models.CharField(max_length=255, verbose_name=u'Telefon', null=True, blank=True)
    fax = models.CharField(max_length=255, verbose_name=u'Fax', null=True, blank=True)
    email = models.CharField(max_length=255, verbose_name=u'E-mail')

    class Meta:
        app_label = 'crm'
        verbose_name = u'Placówka medyczna'
        verbose_name_plural = u'Placówki medyczne'

    def __str__(self):
        return self.name


class Location(models.Model):
    history = DiffedHistoricalRecords()
    staff_pks = models.TextField(max_length=4096, blank=True, null=True, verbose_name=u'Personel')

    name = models.CharField(max_length=255, verbose_name=u'Nazwa')
    description = models.TextField(max_length=4096, null=True, blank=True, verbose_name=u'Opis')
    street = models.CharField(max_length=255, verbose_name=u'Ulica')
    street_number = models.CharField(max_length=255, verbose_name=u'Nr posesji')
    postal_code = models.CharField(max_length=255, verbose_name=u'Kod pocztowy')
    city = models.CharField(max_length=255, verbose_name=u'Miejscowość')
    person = models.ForeignKey(User, verbose_name=u'Osoba', related_name='person', on_delete=models.CASCADE)
    staff = models.ManyToManyField(User, verbose_name=u'Personel', related_name='staff', blank=True)
    telephone = models.CharField(max_length=255, verbose_name=u'Telefon', null=True, blank=True)
    fax = models.CharField(max_length=255, verbose_name=u'Fax', null=True, blank=True)
    email = models.CharField(max_length=255, verbose_name=u'E-mail')

    custom_m2m_history = {
        "staff_pks": ["crm.models.UserProfile", "staff"]
    }

    class Meta:
        verbose_name = u'Lokalizacja'
        verbose_name_plural = u'Lokalizacje'
        ordering = ['name', ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # try to get original object
        if self.pk:
            original = Location.objects.get(pk=self.pk)
        else:
            original = None

        # save object
        super(Location, self).save(*args, **kwargs)

        person_changed = True

        devices = cmms.models.Device.objects.filter(location=self)
        devices_ids = [i.pk for i in devices]

        # compare changes, just to see if there is any reason in updating permissions
        if original:
            if self.person == original.person:
                person_changed = False

        # set permission if person_responsible_changed
        if person_changed:
            # setup_permissions.delay(person, list of devices to reset, list of devices to set permissions)
            if original and original.person:
                if not original.person.has_perm("cmms.view_all_devices"):
                    utils.tasks.setup_permissions.delay(original.person.pk, devices_ids, devices_ids)
            if self.person:
                utils.tasks.setup_permissions.delay(self.person.pk, devices_ids, devices_ids)


class CostCentre(models.Model):
    symbol = models.CharField(max_length=255, verbose_name=u'Symbol')
    name = models.CharField(max_length=255, verbose_name=u'Nazwa')
    description = models.TextField(max_length=4096, null=True, blank=True, verbose_name=u'Opis')

    class Meta:
        verbose_name = u'Centrum kosztowze'
        verbose_name_plural = u'Centra kosztowe'

    def __str__(self):
        return self.name


class Contractor(models.Model):
    history = DiffedHistoricalRecords()
    staff_pks = models.TextField(max_length=4096, blank=True, null=True, verbose_name=u'Pracownicy')

    name = models.CharField(max_length=255, verbose_name=u'Nazwa')
    NIP = models.BigIntegerField(verbose_name=u'NIP')
    street = models.CharField(max_length=255, verbose_name=u'Ulica')
    street_number = models.CharField(max_length=255, verbose_name=u'Nr posesji')
    postal_code = models.CharField(max_length=255, verbose_name=u'Kod pocztowy')
    city = models.CharField(max_length=255, verbose_name=u'Miejscowość')
    email = models.EmailField(blank=True, null=True)
    staff = models.ManyToManyField(User, verbose_name=u'Pracownicy', related_name='contractor_staff', blank=True)

    custom_m2m_history = {
        "staff_pks": ["crm.models.UserProfile", "staff"]
    }

    class Meta:
        verbose_name = u'Kontrahent'
        verbose_name_plural = u'Kontrahenci'

    def __unicode__(self):
        return self.name


class Invoice(models.Model):
    history = DiffedHistoricalRecords()
    service_pks = models.TextField(max_length=4096, blank=True, null=True, verbose_name=u'Zlecenia')

    id = models.AutoField(primary_key=True, auto_created=True)
    number = models.CharField(max_length=100, verbose_name=u'Numer', unique=True)
    name = models.CharField(max_length=255, verbose_name=u'Nazwa')
    description = models.TextField(max_length=4096, null=True, blank=True, verbose_name=u'Opis')
    scan = models.FileField(upload_to='invoices/', null=True, blank=True, verbose_name=u'Skan')
    net_value = models.DecimalField(verbose_name=u'Wartość netto', max_digits=9, decimal_places=2)
    gross_value = models.DecimalField(verbose_name=u'Wartość brutto', max_digits=9, decimal_places=2)
    contractor = models.CharField(verbose_name=u'Kontrahent', max_length=255, blank=True, null=True)
    hospital = models.CharField(verbose_name=u'Szpital', max_length=255, blank=True, null=True)
    created_by = models.ForeignKey('UserProfile', null=True, blank=True, on_delete=models.CASCADE)
    status = models.IntegerField(choices=CHOICES_INVOICE_STATUS, verbose_name=u'status', null=True, blank=True)
    service = models.ManyToManyField('cmms.Service', verbose_name='Zlecenia')
    date = models.DateField(verbose_name=u'Data faktury')
    payment_date = models.DateField(verbose_name=u'Data płatności', blank=True, null=True)
    created_at = models.DateField(verbose_name=u'Data dodania', auto_now_add=True)
    posting_date = models.DateField(verbose_name=u'Data księgowania', blank=True, null=True)

    custom_m2m_history = {
        "service_pks": ["crm.models.Service", "service"]
    }

    def has_costs_breakdown(self):
        return CostBreakdown.objects.filter(invoice_id=self.id).count() > 0

    def get_services(self):
        invoice_services = InvoiceService.objects.filter(invoice=self)
        services_id = [row.service_id for row in invoice_services]

        return cmms.models.Service.objects.filter(id__in=services_id)

    def is_accepted(self):
        return self.status == 3

    class Meta:
        verbose_name = u'Faktura'
        verbose_name_plural = u'Faktury'

    def __str__(self):
        return "%f" % self.gross_value

    def save(self, *args, **kwargs):
        if not self.status:
            self.status = 1

        super(Invoice, self).save(*args, **kwargs)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey('Invoice', verbose_name=u'Faktura', on_delete=models.CASCADE)
    name = models.CharField(max_length=1024, verbose_name=u'Nazwa')
    symbol = models.CharField(max_length=128, verbose_name=u'Symbol')
    net_price = models.DecimalField(verbose_name=u'Cena netto', max_digits=9, decimal_places=2)
    amount = models.IntegerField(verbose_name=u'Ilość')
    net_cost = models.DecimalField(verbose_name=u'Koszt netto', max_digits=9, decimal_places=2)
    gross_cost = models.DecimalField(verbose_name=u'Koszt brutto', max_digits=9, decimal_places=2)
    vat = models.IntegerField(choices=CHOICES_VAT)

    class Meta:
        verbose_name = u'Pozycja faktury'
        verbose_name_plural = u'Pozycje faktury'

    def __str__(self):
        return self.name


class InvoiceService(models.Model):
    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE)
    service = models.ForeignKey('cmms.Service', on_delete=models.CASCADE)


class CostBreakdown(models.Model):
    invoice = models.ForeignKey('Invoice', verbose_name=u'Faktura', on_delete=models.CASCADE)
    device_name = models.CharField(verbose_name=u'Urządzenie', max_length=255)
    device_id = models.IntegerField(verbose_name=u'ID urządzenia')
    device_manufacturer = models.CharField(verbose_name=u'Producent urządzenia', max_length=255)
    device_model = models.CharField(verbose_name=u'Model urządzenia', max_length=255)
    device_serial_number = models.CharField(verbose_name=u'Numer seryjny urządzenia', max_length=255)
    device_inventory_number = models.CharField(verbose_name=u'Numer inwentarzowy urządzenia', max_length=255)
    cost_center_name = models.CharField(verbose_name=u'Nazwa Cetrum Kosztowego', max_length=255)
    cost_center_symbol = models.CharField(verbose_name=u'Symbol Centrum Kosztowego', max_length=255)
    cost_center_description = models.CharField(verbose_name=u'Opis Centrum Kosztowego', max_length=255)
    cost_center_id = models.IntegerField(verbose_name=u'ID Centrum Kosztowego')
    net_cost = models.DecimalField(verbose_name=u'Koszt netto', max_digits=9, decimal_places=2)
    gross_cost = models.DecimalField(verbose_name=u'Koszt brutto', max_digits=9, decimal_places=2)

    def __str__(self):
        return "%s %s" % (self.invoice.name, self.device_name)

    class Meta:
        verbose_name = u'Podział kosztów'
        verbose_name_plural = u'Podział kosztów'

        permissions = (
            ("view_cost_chart", u"Może oglądać wykres podziału kosztów"),        )