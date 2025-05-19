from django import forms
from django.contrib import admin
from django.forms.widgets import Textarea, TextInput


class CalendarEventForm(forms.Form):
    title = forms.CharField(widget=Textarea(attrs={'rows': 2}), required=True, label='Treść')
    start_date = forms.DateTimeField(widget=TextInput, required=True, label='Data')


class CalendarEventAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget = admin.widgets.AdminTextareaWidget()
