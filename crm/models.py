from django.db import models

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
