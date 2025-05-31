from django import forms
from cmms.models import Inspection, Mileage


class InspectionForm(forms.ModelForm):
    class Meta:
        model = Inspection
        exclude = []


class InspectionEventForm(forms.ModelForm):
    class Meta:
        model = Inspection
        exclude = ("priority", "duration_time", "duration_period", "type")


class MileageForm(forms.ModelForm):
    required_css_class = 'required'

    def __init__(self, *args, **kwargs):
        self.user = None
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if request:
            self.user = request.user

    class Meta:
        model = Mileage
        fields = ('state', 'status', 'remarks')

    def clean(self):
        cleaned_data = super().clean()
        if self.instance:
            old_state = self.instance.state
            new_state = cleaned_data.get('state')

            if old_state is not None and new_state is not None and old_state > new_state:
                raise forms.ValidationError("Nowy stan licznika nie może być mniejszy od poprzedniego")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()

        return instance


class NewMileageForm(forms.ModelForm):
    required_css_class = 'required'

    class Meta:
        model = Mileage
        fields = ('device', 'state_initial', 'state_warning', 'warning', 'state_max', 'status', 'remarks')


class PassportManagerForm(forms.Form):
    is_service = forms.BooleanField(
        label="Przegląd",
        initial=False,
        required=False
    )
    devices = forms.CharField(widget=forms.HiddenInput)
    text = forms.CharField(
        widget=forms.Textarea(attrs={"style": "width: 99%;"}),
        initial=(
            "Wykonano [naprawę | przegląd okresowy] zgodnie z zaleceniami producenta.\n"
            "Wymieniono: [podać części zamienne].\n"
            "Nr protokołu serwisowego: [podać nr protokołu].\n"
            "Sprzęt [sprawny | niesprawny | warunkowo dopuszczony do eksploatacji].\n"
            "Zalecenia serwisowe: [podać zalecenia].\n"
            "Data następnej czynności serwisowej: [podać przybliżoną datę].\n\n"
            "[osoba wykonująca czynności serwisowe / nazwa firmy]\n"
            "Nr powiązanego nr #ccc"
        )
    )
