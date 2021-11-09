from django import forms

from rfi.models import MasterRfiCatalog

unique_receivers = MasterRfiCatalog.objects.values_list(
    "frontend", flat=True
).distinct()


class QueryForm(forms.Form):
    receivers = forms.MultipleChoiceField(
        label="Receivers", choices=[(r, r) for r in unique_receivers], required=False
    )
    frequency = forms.FloatField(label="Frequency (MHz)", required=False)
    buffer = forms.FloatField(label="+/- MHz", required=False)
    start = forms.DateField(label="Start", required=False)
    end = forms.DateField(label="End", required=False)
