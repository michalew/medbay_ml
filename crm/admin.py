from django.contrib import admin
from django import forms
from .models import Hospital


class HospitalAdminForm(forms.ModelForm):
    class Meta:
        model = Hospital
        fields = '__all__'

    class Media:
        js = ('js/fetch_company_data.js',)


class HospitalAdmin(admin.ModelAdmin):
    form = HospitalAdminForm
    fieldsets = (
        (None, {
            'fields': ('NIP', 'name', 'REGON', 'KRS', 'street', 'street_number', 'postal_code', 'city', 'email')
        }),
        ('Dodatkowe informacje', {
            'fields': ('logo', 'telephone', 'fax'),
        }),
    )


admin.site.register(Hospital, HospitalAdmin)
