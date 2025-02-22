from django.db import models

# Create your models here.
class Genre(models.Model):
    #history = DiffedHistoricalRecords()
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