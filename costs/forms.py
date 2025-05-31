from django import forms


class CostRangeForm(forms.Form):
    start_date = forms.DateTimeField(widget=forms.TextInput, required=True, label=u'Od')
    end_date = forms.DateTimeField(widget=forms.TextInput, required=True, label=u'Do')
    device_id = forms.IntegerField(widget=forms.HiddenInput, required=True)