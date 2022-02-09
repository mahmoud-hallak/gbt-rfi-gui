from django import forms

from rfi.models import Frontend


class QueryForm(forms.Form):
    receivers = forms.ModelMultipleChoiceField(
        queryset=Frontend.objects.all(), label="Receivers", required=False
    )
    frequency = forms.FloatField(label="Frequency (MHz)", required=False)
    buffer = forms.FloatField(label="+/- MHz", required=False)
    date = forms.DateField(label="Date", required=False)
    start = forms.DateField(label="Start", required=False)
    end = forms.DateField(label="End", required=False)
