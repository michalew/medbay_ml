from calendar import HTMLCalendar, month_name
from datetime import datetime, date
from itertools import groupby

from dateutil.relativedelta import relativedelta
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import Q
from django.forms import ModelForm
from django.utils.html import conditional_escape as esc
from django.utils.safestring import mark_safe

from config import settings
from crm.models import Invoice, Contractor, Location, CostCentre, Hospital, UserProfile
from utils.models import DiffedHistoricalRecords
from utils.tasks import setup_permissions
from .managers import DocumentManager
from .tasks import mileage_remind

sendfile_storage = FileSystemStorage(location=settings.SENDFILE_ROOT)

# Create your models here.
GROUP_CHOICES = (
    (1, u'Aparatura medyczna'),
    (2, u'Sprzęt pomiarowy'),
    (3, u'Infrastruktura'),
    (4, u'Sprzęt IT'),
)
TICKET_SORT_CHOICES = (
    (0, 'Sprawdzenie'),
    (1, 'Naprawa'),
    (2, u'Przegląd'),  # moze byc cykliczny!
    (3, u'Sprawdzenie bezpieczeństwa'),
    (4, 'Aktualizacja oprogramowania'),
    (5, 'Legalizacja'),
    (6, 'Wzorcowanie'),
    (7, 'Konserwacja'),
)

TICKET_STATUS_CHOICES = (
    (99, '---------'),
    (0, u'Otwarte'),
    (1, u'Nowe'),  # nie zmieniaj tego 1 dla statusu Nowe
    (2, u'Zamknięte'),
    (3, u'Przeterminowane'),
    (4, u'Odrzucone'),
    (5, u'Anulowane'),
    # nie zmieniaj tej 6 dla statusu planowane, odniesienie w save dla Inspection.
    (6, u'Planowane'),
)

TICKET_PRIORITY_CHOICES = (
    (99, '----------'),
    (0, 'niski'),
    (1, 'normalny'),
    (2, 'wysoki'),
    (3, 'krytyczny'),
)

SERVICE_STATUS_CHOICES = (
    (99, u'---------'),
    (0, u'nowe'),
    (1, u'zapytanie ofertowe'),
    (2, u'akceptacja oferty'),
    (3, u'w realizacji'),
    (4, u'wykonane'),
    (5, u'zamknięte'),
)
SERVICE_SORT_CHOICES = (
    (0, u'Wewnętrzne'),
    (1, u'Firma zewnętrzna'),
)

ACCESS_CHOICES = (
    (0, u'Prywatny'),
    (1, u'Publiczny'),
)

# status licznika (aktywny, nieaktywny, zakończony)
MILEAGE_STATUS_CHOICES = (
    (0, 'Aktywny'),
    (1, 'Nieaktywny'),
    (2, u'Zakończony'),
)

# status (Nowa, w użyciu, wycofana, skasowana, uszkodzona)
DEVICE_STATUS_CHOICES = (
    (99, '-----------'),
    (0, 'Nowe'),
    (1, u'W użyciu'),
    (2, 'Wycofane'),
    (3, 'Skasowane'),
    (4, 'Uszkodzone'),
)
DOCUMENT_SORT_CHOICES = (
    (11, u'Akceptacja oferty'),
    (7, u'Certyfikat'),
    (8, u'Faktura'),
    (0, u'Instrukcja'),
    (1, u'Karta gwarancyjna'),
    (12, u'Komunikat bezpieczeństwa'),
    (9, u'Kasacja'),
    (14, u'Oferta'),
    (2, u'Paszport'),
    (6, u'Raport serwisowy'),
    (13, u'Umowa'),
    (5, u'Umowa serwisowa'),
    (3, u'Załącznik'),
    (4, u'Zlecenie'),
    (10, u'Zapytanie ofertowe'),
    (99, u' - Inny - '),
)

INSPECTION_TYPES = (
    (1, u"Przegląd"),
    (2, u"Konserwacja"),
)


class Calendar(HTMLCalendar):
    def __init__(self, workouts):
        super(Calendar, self).__init__()
        self.workouts = self.group_by_day(workouts)

    def formatday(self, day, weekday):
        if day != 0:
            cssclass = self.cssclasses[weekday]
            if date.today() == date(self.year, self.month, day):
                cssclass += ' today'
            if day in self.workouts:
                cssclass += ' filled'
                body = ['<ul>']
                for workout in self.workouts[day]:
                    body.append('<li>')
                    # body.append('<a href="/a/cmms/service/%s">' % workout.pk)
                    body.append(
                        '<a target="_blank" href="/a/cmms/ticket/%s/">' % workout.pk)
                    body.append(esc(workout.get_sort_name()))
                    body.append('</a></li>')
                body.append('</ul>')
                return self.day_cell(cssclass, '%d %s' % (day, ''.join(body)))
            return self.day_cell(cssclass, day)
        return self.day_cell('noday', '&nbsp;')

    def navigation(self, year, month):
        cdate = date(year, month, 1)
        pdate = cdate + relativedelta(months=-1)
        ndate = cdate + relativedelta(months=+1)
        mn = month_name[month]
        return '<tr><th colspan="7" class="month"><a href="/kalendarz/%s/%s">&laquo;</a><strong>%s %s</strong><a href="/kalendarz/%s/%s">&raquo;</a></th></tr>' % (
            pdate.year, pdate.month, mn, year, ndate.year, ndate.month)

    def formatmonth(self, year, month):
        self.year, self.month = year, month
        v = []
        a = v.append
        a('<table border="0" cellpadding="0" cellspacing="0" class="month">')
        a('\n')
        a(self.navigation(year, month))
        a('\n<tr><th colspan="7">&nbsp;</th></tr>')
        a(self.formatweekheader())
        a('\n')
        for week in self.monthdays2calendar(year, month):
            a(self.formatweek(week))
            a('\n')
        a('\n<tr><th colspan="7">&nbsp;</th></tr>')
        a(self.navigation(year, month))
        a('</table>')
        a('\n')
        return ''.join(v)

        # return super(Calendar, self).formatmonth(year, month)

    def group_by_day(self, workouts):
        def field(workout): return workout.timestamp.day

        return dict(
            [(day, list(items)) for day, items in groupby(workouts, field)]
        )

    def day_cell(self, cssclass, body):
        return '<td class="%s">%s</td>' % (cssclass, body)


class Make(models.Model):
    history = DiffedHistoricalRecords()
    name = models.CharField(max_length=255, verbose_name=u'Nazwa')

    class Meta:
        verbose_name = u'Producent'
        verbose_name_plural = u'Producenci'
        ordering = ['name', ]

    def __str__(self):
        return self.name


class Genre(models.Model):
    history = DiffedHistoricalRecords()
    symbol = models.CharField(max_length=32, verbose_name=u'Symbol')
    name = models.CharField(max_length=1024, verbose_name=u'Nazwa')
    description = models.TextField(
        max_length=4096, null=True, blank=True, verbose_name=u'Opis')

    class Meta:
        verbose_name = u'Rodzaj urządzenia'
        verbose_name_plural = u'Rodzaje urządzeń'
        ordering = ['name', 'symbol', ]

    def __str__(self):
        return self.name


class Device(models.Model):
    history = DiffedHistoricalRecords()
    document_pks = models.TextField(
        max_length=4096, blank=True, null=True, verbose_name=u'Dokumenty')
    # valid_lookups = ('group__id')
    # def lookup_allowed(self, lookup, *args, **kwargs):
    #    if lookup.startswith(self.valid_lookups):
    #        return True
    #    return super(Device, self).lookup_allowed(lookup, *args, **kwargs)

    name = models.CharField(max_length=255, verbose_name=u'Nazwa')
    genre = models.ForeignKey(Genre, verbose_name=u'Rodzaj', on_delete=models.PROTECT)
    make = models.ForeignKey(Make, verbose_name=u'Producent', on_delete=models.PROTECT)
    model = models.CharField(max_length=255, verbose_name=u'Model')
    serial_number = models.CharField(
        max_length=255, verbose_name=u'Nr seryjny')
    inventory_number = models.CharField(
        max_length=255, verbose_name=u'Nr inwentarzowy')
    udt_number = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=u'Nr UDT')
    # passport_number = models.CharField(max_length=255, verbose_name='Nr paszportu')
    group = models.IntegerField(
        choices=GROUP_CHOICES, default=1, null=True, blank=True, verbose_name=u'Grupa')
    cost_centre = models.ForeignKey(
        CostCentre, null=True, blank=True, verbose_name=u'Centrum Kosztowe', on_delete=models.PROTECT)
    location = models.ForeignKey(
        Location, null=True, blank=True, verbose_name=u'Lokalizacja', on_delete=models.PROTECT)
    location_place = models.CharField(
        "Miejsce", max_length=255, null=True, blank=True)

    # service dates
    date_service = models.DateField(
        blank=True, null=True, verbose_name=u"Aktualny przegląd")
    date_next_service = models.DateField(
        blank=True, null=True, verbose_name=u"Następny przegląd")  # cache
    service_interval = models.PositiveIntegerField(
        default=1, verbose_name=u"Następny przegląd za")
    service_interval_type = models.PositiveIntegerField(choices=(
        (0, u"tygodni"), (1, u"miesięcy"), (2, u"lat")
    ), default=2, verbose_name="Rodzaj interwału")

    date_manufactured = models.DateField(
        blank=True, null=True, verbose_name=u'Data produkcji')
    date_bought = models.DateField(
        blank=True, null=True, verbose_name=u'Data zakupu')
    date_warranty = models.DateField(
        blank=True, null=True, verbose_name=u'Data upływu gwarancji')
    remarks = models.TextField(
        max_length=4096, blank=True, null=True, verbose_name=u'Uwagi')
    person_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name='responsible', verbose_name=u'Osoba odpowiedzialna', on_delete=models.PROTECT)
    technical_supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name='supervisor', verbose_name=u'Nadzór techniczny', on_delete=models.PROTECT)
    status = models.IntegerField(
        choices=DEVICE_STATUS_CHOICES, default=0, verbose_name=u'Status')
    # TODO czy to nie powinien byc userprofile ?? i czy to ma tu byc?? ( jest w zleceniu
    contractor = models.ForeignKey(
        Contractor, null=True, blank=True, verbose_name=u'Firma serwisująca', on_delete=models.PROTECT)

    related_models = ["cmms.models.DeviceGallery",
                      "cmms.models.DevicePassport", ]

    custom_m2m_history = {
        "document_pks": ["cmms.models.Document", "document_set"],
    }

    # TODO:
    # obrazy (osobny model; a moze nie?)
    # dostawca (np. dystrybutor) - czy moze byc wsrod wszystkich kontrahentow?
    # firma serwisujaca (kontrahent) - patrz Service (?)

    class Meta:
        verbose_name = u'Urządzenie'
        verbose_name_plural = u'Urządzenia'
        ordering = ['-id', ]

        permissions = (
            ("custom_view_device", u"Może zobaczyć swoje urządzenia"),
            ("view_all_devices", u"Może zobaczyć wszystkie urządzenia"),
            ("view_changelist_device", u"Może zobaczyć listę urządzeń (CRM)"),
            ("view_device_class_chart", u"Może wyświetlać wykres klas urządzeń"),
        )

    def __str__(self):
        return "%s" % self.name

    def get_status_name(self):
        return "%s" % dict(DEVICE_STATUS_CHOICES)[self.status]

    def _xls_get_status_name(self):
        return self.get_status_name()

    _xls_get_status_name.short_description = u"Status"

    def get_group_name(self):
        return "%s" % dict(GROUP_CHOICES)[self.group]

    def _xls_get_group_name(self):
        return self.get_group_name()

    _xls_get_group_name.short_description = u"Grupa"

    def get_absolute_url(self):
        return "/a/cmms/device/%d" % self.id

    def get_absolute_url_with_label(self):
        return mark_safe("<a target='_blank' href='%s'>%s</a>" % (self.get_absolute_url(), self.inventory_number))

    def get_ticket_set_as_inspection(self):
        return Ticket.objects.prefetch_related("device").filter(device=self, sort__in=[2, 7])

    def has_service(self):
        # get a list of related documents
        related = Document.objects.filter(
            device=self, sort=5, date_expiration__gte=date.today())

        return related.count() > 0

    @property
    def passport_entries(self):
        return self.devicepassport_set.order_by('added_date')

    def get_date_next_service(self):
        delta_kwargs = {
            "years": self.service_interval if self.service_interval_type == 2 else 0,
            "months": self.service_interval if self.service_interval_type == 1 else 0,
            "weeks": self.service_interval if self.service_interval_type == 0 else 0
        }
        return self.date_service + relativedelta(**delta_kwargs) if self.date_service else None

    date_next_service.short_description = u"Następny przegląd"

    def get_device_class(self, year=None):
        """
        Zwraca klasę urządzenia
        Klasa 1: od 0 do 2 lat
        Klasa 2: od 3 do 6 lat
        Klasa 3: od 7 do 9 lat
        Klasa 4: 10 i więcej lat
        """
        now = datetime.now()

        if year == None:
            year = now.year

        if self.date_manufactured:
            years_past = year - self.date_manufactured.year
        else:
            return 0

        if self.date_manufactured.year > year:
            return -1
        if self.date_bought:
            if self.date_bought.year > year:
                return -1

        if years_past < 0:
            return -1  # ignore the future
        elif years_past <= 2:
            return 1
        elif years_past <= 6:
            return 2
        elif years_past <= 9:
            return 3
        else:
            return 4

    def get_related_emails(self):
        """
        Returns lists of addresses of all people we should e-mail when things happen.
        :return: list of addresses
        """
        # get people from fields in self
        people = [
            self.person_responsible,
            self.technical_supervisor,
        ]

        # everyone who can see all devices
        all_users = UserProfile.objects.all()
        for user in all_users:
            if user.has_perm("cmms.view_all_devices"):
                people += [user, ]

        mails = [person.email for person in people if person]

        # deduplicate
        mails = list(set(mails))

        # return list of adresses
        return mails

    def save(self, *args, **kwargs):
        # try to get original object
        if self.pk:
            original = Device.objects.get(pk=self.pk)
        else:
            original = None

        self.date_next_service = self.get_date_next_service()

        # save object
        super(Device, self).save(*args, **kwargs)

        location_changed = True
        person_responsible_changed = True
        contractor_changed = True

        # compare changes, just to see if there is any reason in updating permissions
        if original:
            if self.location == original.location:
                location_changed = False
            if self.person_responsible == original.person_responsible:
                person_responsible_changed = False
            if self.contractor == original.contractor:
                contractor_changed = False

        # make sure everyone with cmms.view_all_devices can see it
        view_all = UserProfile.objects.all()
        for user in view_all:
            if user.has_perm("cmms.view_all_devices"):
                if original:
                    setup_permissions.delay(user.pk, [self.pk], [self.pk])
                else:
                    setup_permissions(user.pk, [self.pk], [self.pk])

        # set permission if person_responsible_changed
        if person_responsible_changed:
            # setup_permissions.delay(person, list of devices to reset, list of devices to set permissions)
            if original and original.person_responsible:
                if not original.person_responsible.has_perm("cmms.view_all_devices"):
                    setup_permissions.delay(
                        original.person_responsible.pk, [self.pk], [])
            if self.person_responsible:
                setup_permissions.delay(
                    self.person_responsible.pk, [self.pk], [self.pk])

        # update permissions if location changed
        if location_changed:
            # get users from old and new location
            if original and original.location:
                old_users = UserProfile.objects.filter(
                    Q(staff=original.location) | Q(person=original.location))
                if self.person_responsible:
                    old_users.exclude(pk=self.person_responsible.pk)
            else:
                old_users = ()
            if self.location:
                new_users = UserProfile.objects.filter(
                    Q(staff=self.location) | Q(person=self.location))
            else:
                new_users = ()

            # remove permissions
            for user in old_users:
                if not user.has_perm("cmms.view_all_devices"):
                    setup_permissions.delay(user.pk, [self.pk], [])

            # setup permissions
            for user in new_users:
                setup_permissions.delay(user.pk, [self.pk], [self.pk])

        if contractor_changed:
            # get old and new contractors
            if original and original.contractor:
                old_users = UserProfile.objects.filter(
                    contractor_staff=original.contractor)
                if self.person_responsible:
                    old_users = old_users.exclude(
                        pk=self.person_responsible.pk)
            else:
                old_users = ()
            if self.contractor:
                new_users = UserProfile.objects.filter(
                    contractor_staff=self.contractor)
            else:
                new_users = ()

            # remove permissions
            for user in old_users:
                if not user.has_perm("cmms.view_all_devices"):
                    setup_permissions.delay(user.pk, [self.pk], [])

            # setup permissions
            for user in new_users:
                setup_permissions.delay(user.pk, [self.pk], [self.pk])


class DeviceGallery(models.Model):
    """Model to store images of gallery devices."""

    device = models.ForeignKey(Device, verbose_name="Urządzenie", on_delete=models.PROTECT)
    image = models.ImageField("Zdjecie", upload_to="devices/gallery")
    description = models.TextField(u"Opis", blank=True)
    is_visible = models.BooleanField(u"Czy widoczne", default=True)
    added_date = models.DateField(u"Data dodania", auto_now_add=True)
    added_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Użytkownik dodający",
        blank=True, null=True, on_delete=models.PROTECT)
    history = DiffedHistoricalRecords()

    def __str__(self):
        return "Zdjęcie: %s" % self.image


class DevicePassport(models.Model):
    history = DiffedHistoricalRecords()

    device = models.ForeignKey(Device, verbose_name=u"Urządzenie", on_delete=models.PROTECT)
    content = models.TextField(u"Treść", blank=True)
    added_date = models.DateField(u"Data wpisu", default=date.today)
    added_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=u"Użytkownik dodający",
        blank=True, null=True, on_delete=models.PROTECT)

    def __str__(self):
        return u"Wpis do paszportu: %s" % self.content

    class Meta:
        verbose_name = u"Wpis do paszportu"
        verbose_name_plural = u"Wpisy do paszportu"

        permissions = (
            ("update_devicepassport", u"Może edytować wpisy do paszportu"),
            ("view_devicepassport_history",
             u"Może zobaczyć historię zmian wpisów do paszportu"),
        )


class Kit(models.Model):
    device = models.ForeignKey(Device, verbose_name=u'Urządzenie', on_delete=models.PROTECT)
    name = models.CharField(max_length=255, verbose_name=u'Nazwa')
    make = models.CharField(max_length=255, blank=True,
                            null=True, verbose_name=u'Producent')
    model = models.CharField(max_length=255, blank=True,
                             null=True, verbose_name=u'Model')
    serial_number = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=u'Numer seryjny')
    description = models.TextField(
        max_length=4096, blank=True, null=True, verbose_name=u'Opis')

    class Meta:
        verbose_name = u'Wyposażenie'
        verbose_name_plural = u'Wyposażenie/części'

    def __unicode__(self):
        return "%s: %s" % (self.device.name, self.name)


class Unit(models.Model):
    name = models.CharField(max_length=200, verbose_name=u'Nazwa')
    unit = models.CharField(max_length=50, verbose_name=u'Krótka nazwa')

    class Meta:
        verbose_name = u'Jednostka'
        verbose_name_plural = u'Jednostki'

    def __str__(self):
        return "%s [%s]" % (self.name, self.unit)


class Mileage(models.Model):
    device = models.ForeignKey(Device, verbose_name=u'Urządzenie', on_delete=models.PROTECT)
    name = models.CharField(
        max_length=255, verbose_name=u'Nazwa', default="Licznik: ")
    unit = models.ForeignKey(Unit, verbose_name=u'Jednostka', null=True, on_delete=models.PROTECT)

    state_initial = models.IntegerField(
        verbose_name=u'Stan minimalny', null=True)

    state = models.IntegerField(verbose_name=u'Stan licznika', null=True)

    state_warning = models.IntegerField(
        verbose_name=u'Stan graniczny licznika')
    warning = models.TextField(max_length=255, blank=True, null=True,
                               verbose_name=u'Monit po przekroczeniu wartości granicznej')

    state_max = models.IntegerField(verbose_name=u'Maksymalny stan licznika')

    remarks = models.TextField(
        max_length=4096, blank=True, null=True, verbose_name=u'Uwagi')
    remarks_ui = models.TextField(
        max_length=4096, blank=True, null=True, verbose_name=u"Uwagi")
    status = models.IntegerField(
        choices=MILEAGE_STATUS_CHOICES, default=0, verbose_name=u'Status')

    date = models.DateField(verbose_name=u'Data utworzenia', auto_now=True)
    person_creating = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        verbose_name=u'Utworzony przez', on_delete=models.PROTECT)

    history = DiffedHistoricalRecords()

    ignored_keys = ['remarks_ui', ]

    class Meta:
        verbose_name = u'Licznik'
        verbose_name_plural = u'Liczniki'

        permissions = (
            ("view_changelist_mileage", u"Może zobaczyć listę liczników"),
            ("update_mileage", u"Może wprowadzać licznik (serwis)"),
            ("reset_mileage", u"Może resetować licznik"),
        )

    def __str__(self):
        return u"%s: %s, %s" % (self.device.name, self.name, self.state)

    def get_device(self):
        d = self.device
        return "%s: %s" % (d.inventory_number, d.name)

    get_device.short_description = u"Urządzenia"

    def get_percentage(self):
        # calculate percentage
        percentage = float(self.state) / float(self.state_max)
        return '{:.2%}'.format(percentage)

    get_percentage.short_description = u"Procent zużycia"

    def remind(self):
        if int(self.state) >= int(self.state_warning) and int(self.status) == 0:
            mileage_remind.delay(self.pk)

    def save(self, *args, **kwargs):
        # reset current status to initial if object is new
        if self.pk is None:
            self.state = self.state_initial

        # fail if initial state is bigger than max state
        if self.state_initial > self.state_max:
            raise Exception(
                u"Stan początkowy licznika musi być mniejszy niż wartość końcowa")

        # fail if warning state is not between initial and maximum
        if self.state_warning > self.state_max or self.state_warning < self.state_initial:
            raise Exception(
                u"Wartość graniczna musi być pomiędzy początkową, a końcową")

        # fail if state is lower than initial state
        if self.state < self.state_initial:
            raise Exception(
                u"Wartość musi być większa lub równa wartości minimalnej")

        # send notification if required
        self.remind()

        # save the data
        super(Mileage, self).save(*args, **kwargs)

    def get_status_name(self):
        return "%s" % dict(MILEAGE_STATUS_CHOICES)[self.status]


class Ticket(models.Model):
    history = DiffedHistoricalRecords()
    device_pks = models.TextField(
        max_length=4096, blank=True, null=True, verbose_name=u'Urządzenia')
    document_pks = models.TextField(
        max_length=4096, blank=True, null=True, verbose_name=u'Dokumenty')

    device = models.ManyToManyField(
        Device, verbose_name=u'Urządzenie', blank=True)
    created_ticket_date = models.DateTimeField(auto_now_add=True,
                                               verbose_name=u'Data dodania',
                                               blank=True, null=True)
    timestamp = models.DateField(default=datetime.now, verbose_name=u'Data rozpoczęcia')
    sort = models.IntegerField(
        choices=TICKET_SORT_CHOICES, default=0, verbose_name=u'Rodzaj zgłoszenia')
    cyclic = models.BooleanField(verbose_name=u'Cykliczny?', default=False)
    description = models.TextField(
        max_length=4096, null=True, blank=True, verbose_name=u'Opis')
    status = models.IntegerField(
        choices=TICKET_STATUS_CHOICES, default=1, verbose_name=u'Status')
    person_creating = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, verbose_name=u'Zgłaszający', on_delete=models.PROTECT)
    person_closing = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                       blank=True,
                                       verbose_name=u'Osoba zamykająca',
                                       related_name='closing', on_delete=models.PROTECT)
    date_closing = models.DateField(
        verbose_name=u'Data zamknięcia', blank=True, null=True, editable=True)
    priority = models.IntegerField(
        choices=TICKET_PRIORITY_CHOICES, default=1, verbose_name=u'Priorytet')
    cost = models.CharField(max_length=32, null=True,
                            blank=True, verbose_name=u'Koszt brutto')
    summation = models.TextField(
        max_length=4096, blank=True, verbose_name=u'Podsumowanie')

    date_finish = models.DateField(
        verbose_name=u'Data zakończenia', blank=True, null=True, editable=True)
    planned_date_finish = models.DateField(
        verbose_name=u'Planowana data zakończenia', blank=True, null=True)
    person_completing = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                          blank=True,
                                          related_name='completing',
                                          verbose_name=u'Odbiorca zlecenia', on_delete=models.PROTECT)
    contractor = models.ForeignKey(Contractor, null=True, blank=True,
                                   verbose_name=u'Firma serwisująca',
                                   related_name="contractor_set",
                                   on_delete=models.PROTECT)  # TODO czy to nie powinien byc userprofile ?? I CZY TO W OGOLE POWINNO TU BYC??

    contractor_execute = models.ForeignKey(Contractor, null=True, blank=True,
                                           verbose_name=u'Firma wykonująca',
                                           related_name="contractor_execute_set", on_delete=models.PROTECT)
    person_execute = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                       blank=True,
                                       related_name='persons_execute',
                                       verbose_name=u'Osoba wykonująca', on_delete=models.PROTECT)
    planned_date_execute = models.DateField(
        verbose_name=u'Planowana data wykonania', blank=True, null=True)
    date_execute = models.DateField(
        verbose_name=u'Data wykonania', blank=True, null=True, editable=True)
    inspection_type = models.IntegerField(
        u"Typ przeglądu", choices=INSPECTION_TYPES, default=1)
    from_which_inspection = models.ForeignKey(
        "Inspection", verbose_name=u"Z którego przeglądu", blank=True, null=True, on_delete=models.PROTECT)
    from_which_inspection_item = models.ForeignKey("InspectionItem", verbose_name=u"Z którego zdarzenia przeglądu",
                                                   blank=True, null=True, on_delete=models.PROTECT)

    custom_m2m_history = {
        "device_pks": ["cmms.models.Device", "device"],
        "document_pks": ["cmms.models.Document", "document_set"],
    }

    class Meta:
        verbose_name = u'Zgłoszenie'
        verbose_name_plural = u'Zgłoszenia'
        ordering = ['-timestamp', ]
        permissions = (
            ("view_changelist_ticket", u"Może zobaczyć listę Zgłoszeń"),
            ("change_devices_ticket", u"Może zmienić zgłoszone urządzenia do Zgłoszenia"),
            ("change_details_ticket", u"Może edytować szczegóły Zgłoszenia"),
            ("change_description_ticket", u"Może zmienić opis Zgłoszenia"),
            ("change_summation_ticket", u"Może zmienić podsumowanie Zgłoszenia"),
            ("add_comment_ticket", u"Może dodać komentarz do Zgłoszenia"),
            ("add_document_ticket", u"Może dodać dokument do Zgłoszenia"),
            ("view_ticket_chart", u"Może oglądać wykres zgłoszeń"),
        )


    def get_absolute_url(self):
        return "/a/cmms/ticket/%d" % self.id

    def get_absolute_url_with_label(self):
        return mark_safe("<a target='_blank' href='%s'>%s</a>" % (self.get_absolute_url(), self.pk))

    def get_device_name(self):
        arr = self.device.all()
        return "%s" % ", ".join(arr.values_list('name', flat=True))

    def get_sort_name(self):
        return "%s" % dict(TICKET_SORT_CHOICES)[self.sort]

    def get_priority(self):
        return "%s" % dict(TICKET_PRIORITY_CHOICES)[self.priority]

    def get_status_name(self):
        return "%s" % dict(TICKET_STATUS_CHOICES)[self.status]

    def __str__(self):
        return "%s: %s" % (self.get_sort_name(), self.get_device_name())

    def get_devices(self):
        return self.device.all()

    def get_services(self):
        return self.service_set.all()

    def save(self, *args, **kwargs):
        if not self.planned_date_execute:
            now = datetime.now()
            self.planned_date_execute = now + relativedelta(days=7)

        # 🛡️ Konwersje datetime -> date dla pól DateField
        date_fields = [
            'timestamp',
            'date_closing',
            'date_finish',
            'planned_date_finish',
            'planned_date_execute',
            'date_execute',
        ]
        for field in date_fields:
            value = getattr(self, field)
            if isinstance(value, datetime):
                setattr(self, field, value.date())

        super(Ticket, self).save(*args, **kwargs)

    def person_creating_name(self):
        return self.person_creating if self.person_creating else "brak"

    person_creating_name.short_description = person_creating.verbose_name

    def person_closing_name(self):
        return self.person_closing if self.person_closing else "brak"

    person_closing_name.short_description = person_closing.verbose_name

    def _xls_get_devices(self):
        devices = self.device.all()
        arr = []
        for d in devices:
            arr.append("%s: %s; %s; %s; %s" % (d.inventory_number,
                                               d.name, d.make, d.model, d.serial_number))
        return u"\n".join(arr)

    _xls_get_devices.short_description = u"Urządzenia"

    def _xls_get_locations(self):
        devices = self.device.all()
        arr = []
        for d in devices:
            arr.append(u"%s, %s; %s; %s; %s; %s" % (d.cost_centre, d.location,
                                                    d.location.person if d.location else "Brak",
                                                    d.location.telephone if d.location else "Brak",
                                                    d.location.email if d.location else "Brak",
                                                    d.location.fax if d.location else "Brak"))
        return u"\n".join(arr)

    _xls_get_locations.short_description = u"Centrum kosztowe, lokalizacja"

    def get_related_emails(self):
        """
        Returns lists of addresses of all people we should e-mail when things happen.
        :return:
        """
        # get people from fields in self
        people = [
            self.person_creating,
            self.person_closing,
            self.person_execute,
        ]

        mails = [person.email for person in people if person]

        # get all related emails for devices
        for device in self.device.all():
            mails += device.get_related_emails()

        # deduplicate
        mails = list(set(mails))

        # return list of adresses
        return mails


class TicketForm(ModelForm):
    class Meta:
        model = Ticket
        fields = ('sort', 'description',)


class Service(models.Model):
    history = DiffedHistoricalRecords()
    ticket_pks = models.TextField(
        max_length=4096, blank=True, null=True, verbose_name=u'Zgłoszenia')
    document_pks = models.TextField(
        max_length=4096, blank=True, null=True, verbose_name=u'Dokumenty')

    ticket = models.ManyToManyField(Ticket, verbose_name=u'Zgłoszenia')
    hospital = models.ForeignKey(Hospital, verbose_name=u'Szpital', on_delete=models.PROTECT)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=u'Data')
    sort = models.IntegerField(
        choices=SERVICE_SORT_CHOICES, verbose_name=u'Rodzaj')
    person_assigned = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name='assigned', verbose_name=u'Osoba przypisana', on_delete=models.PROTECT)
    description = models.TextField(
        max_length=4096, null=True, blank=True, verbose_name=u'Opis')
    status = models.IntegerField(
        choices=SERVICE_STATUS_CHOICES, default=0, verbose_name=u'Status')
    person_creating = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name='creating', verbose_name=u'Osoba zlecająca', on_delete=models.PROTECT)
    person_completing = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name='completing_service', verbose_name=u'Odbiorca zlecenia', on_delete=models.PROTECT)
    summation = models.TextField(
        max_length=4096, blank=True, verbose_name=u'Podsumowanie')
    date_finish = models.DateField(
        verbose_name=u'Data zakończenia', blank=True, null=True, editable=True)
    contractor = models.ForeignKey(Contractor, null=True, blank=True,
                                   verbose_name=u'Firma serwisująca',
                                   related_name="contractors_set",
                                   on_delete=models.PROTECT)  # TODO czy to nie powinien byc userprofile ??

    contractor_execute = models.ForeignKey(Contractor, null=True, blank=True,
                                           verbose_name=u'Firma wykonująca',
                                           related_name="contractors_execute_set", on_delete=models.PROTECT)
    person_execute = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                       blank=True,
                                       related_name='persons_execute_service',
                                       verbose_name=u'Osoba wykonująca', on_delete=models.PROTECT)
    planned_date_execute = models.DateField(
        verbose_name=u'Planowana data wykonania', blank=True, null=True)
    date_execute = models.DateField(
        verbose_name=u'Data wykonania', blank=True, null=True, editable=True)
    # TODO: czy firma serwisujaca ma byc i dla urzadzenia i dla tego modelu (czy moze byc inna firma serwisujaca w zleceniu niz w urzadzeniu)?

    custom_m2m_history = {
        "ticket_pks": ["cmms.models.Ticket", "ticket"],
        "document_pks": ["cmms.models.Document", "document_set"],
    }

    class Meta:
        verbose_name = u'Zlecenie'
        verbose_name_plural = u'Zlecenia'
        ordering = ['timestamp', ]

        permissions = (
            ("view_changelist_service", u"Może zobaczyć listę Zleceń"),
            ("change_data_service", u"Może zmienić dane Zlecenia"),
            ("change_tickets_service", u"Może zmienić przypisane zgłoszenia"),
            ("add_comment_service", u"Może dodać komentarz do Zlecenia"),
            ("add_document_service", u"Może dodać dokument do Zlecenia"),
            ("change_summation_service", u"Może zmienić podsumowanie Zlecenia"),
        )

    def __str__(self):
        return u"Zlecenie %s" % self.get_sort_name()

    def get_sort_name(self):
        return u"%s" % dict(SERVICE_SORT_CHOICES)[self.sort]

    def _xls_get_sort_name(self):
        return self.get_sort_name()

    _xls_get_sort_name.short_description = u"Rodzaj"

    def get_status_name(self):
        return "%s" % dict(SERVICE_STATUS_CHOICES)[self.status]

    def _xls_get_status_name(self):
        return self.get_status_name()

    _xls_get_status_name.short_description = u"Status"

    def get_tickets(self):
        tickets = ""
        for t in self.ticket.all():
            tickets += "%s; " % t
        return tickets.rstrip("; ")

    def get_absolute_url(self):
        return "/a/cmms/service/%d/" % self.id

    def get_related_emails(self):
        """
        Returns lists of addresses of all people we should e-mail when things happen.
        :return:
        """
        # get people from fields in self
        people = [
            self.person_creating,
            self.person_assigned,
            self.person_completing,
            self.person_execute,
        ]

        mails = [person.email for person in people if person]

        # get all related emails for tickets
        for ticket in self.ticket.all():
            mails += ticket.get_related_emails()

        # deduplicate
        mails = list(set(mails))

        # return list of adresses
        return mails


class ServiceForm(ModelForm):
    required_css_class = 'required'

    class Meta:
        model = Service
        fields = ('sort', 'person_assigned', 'description', 'status',
                  'contractor', 'person_completing', 'hospital')


class Document(models.Model):
    objects = DocumentManager()

    name = models.CharField(max_length=255, verbose_name=u'Nazwa')
    device = models.ManyToManyField(
        Device, blank=True, verbose_name=u'Urządzenie')
    scan = models.FileField(upload_to='documents/', storage=sendfile_storage,
                            null=True, blank=True, verbose_name=u'Plik')
    description = models.TextField(
        max_length=4096, null=True, blank=True, verbose_name=u'Opis')
    sort = models.IntegerField(choices=DOCUMENT_SORT_CHOICES,
                               default=1, null=True, blank=True, verbose_name=u'Rodzaj')
    timestamp = models.DateTimeField(
        auto_now_add=True, verbose_name=u'Data dodania')
    date_document = models.DateField(
        blank=True, null=True, verbose_name=u'Data dokumentu')
    service = models.ManyToManyField(
        Service, blank=True, verbose_name=u'Zlecenie')
    ticket = models.ManyToManyField(
        Ticket, blank=True, verbose_name=u'Zgłoszenie')

    number = models.CharField(
        max_length=255, verbose_name=u'Numer dokumentu', blank=True, null=True)
    date_expiration = models.DateField(verbose_name=u'Data ważności dokumentu', blank=True,
                                       null=True, editable=True)
    date_termination = models.DateField(verbose_name=u'Data wypowiedzenia', blank=True,
                                        null=True, editable=True)
    contractor = models.ForeignKey(
        Contractor, blank=True, verbose_name=u'Kontrahent', null=True, on_delete=models.PROTECT)
    person_adding = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                      blank=True, related_name='adding_person',
                                      verbose_name=u'Osoba dodająca dokument', on_delete=models.PROTECT)
    access = models.IntegerField(
        choices=ACCESS_CHOICES, verbose_name=u'Dostęp', default=1)
    history = DiffedHistoricalRecords()

    class Meta:
        verbose_name = u'Dokument'
        verbose_name_plural = u'Dokumenty'
        ordering = ['timestamp', 'date_document', 'name']

        permissions = (
            ("custom_view_document", u"Może zobaczyć Dokument"),
            ("view_changelist_document", u"Może zobaczyć listę Dokumentów"),
        )

    def __str__(self):
        return "%s" % self.name

    def get_sort_name(self):
        try:
            return "%s" % dict(DOCUMENT_SORT_CHOICES)[self.sort]
        except:
            return self.sort


class Inspection(models.Model):
    INSPECTION_PRIORITY = (
        (1, u"Niski"),
        (2, u"Normalny"),
        (3, u"Wysoki"),
    )

    INSPECTION_DURATION_PERIODS = (
        (1, u"Godzin"),
        (2, u"Dni")
    )

    INSPECTION_CYCLE_PERIODS = (
        (1, u"Dni"),
        (2, u"Tygodni"),
        (3, u"Miesięcy"),
        (4, u"Lat"),
    )

    INSPECTION_RECURRING_PERIODS = (
        (1, u"Dni"),
        (2, u"Miesięcy"),
    )

    name = models.CharField(u"Nazwa", max_length=255)
    type = models.IntegerField(u"Typ", choices=INSPECTION_TYPES, default=1)
    priority = models.IntegerField(
        u"Priorytet", choices=INSPECTION_PRIORITY, default=1)
    duration_time = models.IntegerField(u"Czas trwania", blank=True, null=True)
    duration_period = models.IntegerField(u"Czas trwania (okres)",
                                          choices=INSPECTION_DURATION_PERIODS,
                                          blank=True, null=True)
    description = models.TextField(u"Uwagi", blank=True)
    count_planned_events = models.IntegerField(u"Ilość planowanych zdarzeń")
    cycle_value = models.IntegerField(u"Wartość cyklu", blank=True, null=True)
    cycle_value_period = models.IntegerField(
        u"Okres cyklu", choices=INSPECTION_CYCLE_PERIODS, default=1)
    cycle_date_start = models.DateField(u"Data początkowa cyklu")
    recurring_time = models.IntegerField(u"Nowe zgłoszenia - ilość dni przed")
    recurring_period = models.IntegerField(
        u"Nowe zgłoszenia - okres przed", choices=INSPECTION_RECURRING_PERIODS,
        default=1)
    device_elements = models.TextField(u"Części", blank=True)
    added_date = models.DateTimeField(
        u"Data dodania przeglądu", auto_now_add=True)
    modify_date = models.DateTimeField(u"Data edycji przeglądu", auto_now=True)
    added_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=u"Autor przeglądu", blank=True,
        null=True, on_delete=models.PROTECT)
    history = DiffedHistoricalRecords()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = u"Przegląd"
        verbose_name_plural = u"Przeglądy"

        permissions = (
            ("view_changelist_inspection", u"Może zobaczyć listę przeglądów"),
        )

    def get_absolute_url(self):
        return "/a/cmms/inspection/%s" % self.pk

    def get_absolute_url_with_label(self):
        return mark_safe("<a target='_blank' href='%s'>%s</a>" % (self.get_absolute_url(), self.pk))

    def save(self, *args, **kwargs):
        super(Inspection, self).save(*args, **kwargs)
        for item in self.inspectionitem_set.all():
            item.save(stop_create_tickets=False)
            break

    def delete(self, using=None):
        Ticket.objects.filter(from_which_inspection=self).delete()
        super(Inspection, self).delete(using)


class InspectionDevice(models.Model):
    inspection = models.ForeignKey(Inspection, verbose_name=u"Przegląd", on_delete=models.PROTECT)
    device = models.ForeignKey(Device, verbose_name=u"Urządzenie", on_delete=models.PROTECT)

    class Meta:
        verbose_name = u"Przegląd - urządzenie"
        verbose_name_plural = u"Przegląd - urządzenia"

    def __unicode__(self):
        return u"%s (ID: %s | producent: %s | model: %s | nr inwentarzowy: %s | lokalizacja: %s)" % (
            self.device.name, self.device.pk, self.device.make, self.device.model, self.device.inventory_number,
            self.device.location)


class InspectionItem(models.Model):
    inspection = models.ForeignKey(Inspection, verbose_name=u"Przegląd", on_delete=models.PROTECT)
    name = models.CharField(u"Nazwa", max_length=256)
    planned_date = models.DateField(u"Planowana data wykonania")
    ticket_date = models.DateField(u"Data utworzenia zgłoszenia")
    created_ticket_id = models.CharField(
        u"ID utworzonego zgłoszenia", blank=True, null=True, max_length=256)
    added_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=u"Autor zdarzenia przeglądu",
        blank=True, null=True, on_delete=models.PROTECT)

    def save(self, stop_create_tickets=False, *args, **kwargs):
        super(InspectionItem, self).save(*args, **kwargs)
        if not stop_create_tickets:
            from utils.inspection_utils import create_tickets_from_inspection
            create_tickets_from_inspection(inspection=self.inspection)

    class Meta:
        verbose_name = u"Zdarzenie"
        verbose_name_plural = u"Zdarzenia"

    def __unicode__(self):
        if self.created_ticket_id:
            return mark_safe(u"<a href='/a/cmms/ticket/%s'>ID Utworzonego zgłoszenia: %s</a>" % (self.created_ticket_id,
                                                                                                 self.created_ticket_id))
        return self.name


class InspectionDocument(models.Model):
    inspection = models.ForeignKey(Inspection, verbose_name=u"Przegląd", on_delete=models.PROTECT)
    document = models.ForeignKey(Document, verbose_name=u"Dokument", on_delete=models.PROTECT)

    class Meta:
        verbose_name = u"Przegląd - dokument"
        verbose_name_plural = u"Przegląd - dokumenty"

    def __str__(self):
        return u"%s (ID: %s | rodzaj: %s | data dodania: %s)" % (
            self.document.name, self.document.pk, self.document.sort, self.document.timestamp.strftime("%d-%m-%Y"))
