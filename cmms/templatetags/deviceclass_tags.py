from django.template.defaulttags import register
from cmms.models import Device


@register.filter
def class_by_year(device, year):
    device = Device.objects.get(pk=device)
    return device.get_device_class(year)
