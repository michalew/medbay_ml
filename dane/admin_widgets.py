# -*- coding: utf-8 -*-
from django.contrib.admin.widgets import AdminFileWidget
from django.urls import reverse


class SecuredAdminFileWidget(AdminFileWidget):
    """
    A FileField Widget that shows secure file link
    """
    def __init__(self, attrs={}):
        super(AdminFileWidget, self).__init__(attrs)

    def get_template_substitution_values(self, value):
        """
        Overriden template substitution values
        """
        values = super(AdminFileWidget, self).get_template_substitution_values(
            value)
        if value and value.instance and value.instance.pk:
            values["initial_url"] = reverse('download_document', args=(
                value.instance.pk, )
            )
        return values
