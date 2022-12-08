import datetime

from crispy_forms.bootstrap import AppendedText, FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Submit

from django import forms

from rfi.models import Frontend

MAX_TIME_SPAN = datetime.timedelta(days=365)

# https://getbootstrap.com/docs/4.6/components/forms/
# https://getbootstrap.com/docs/5.0/examples/sidebars/#
# https://getbootstrap.com/docs/4.1/utilities/flex/

class QueryFormHelper(FormHelper):
    layout = Div(
        Div(
            Div("receivers", css_class="col-auto"),
            css_class="row-auto",
        ),
        Div(
            Div(AppendedText("freq_low", "MHz"), css_class="col"),
            css_class="row",
        ),
        Div(
            Div(AppendedText("freq_high", "MHz"), css_class="col"),
            css_class="row",
        ),
        Div(
            Div("date", css_class="col"),
            css_class="row",
        ),
        Div(
            Div("start", css_class="col"),
            css_class="row",
        ),
        Div(
            Div("end", css_class="col"),
            css_class="row",
        ),
        FormActions(
            Submit("submit", "Submit"),
            css_class="",
        ),
        css_class="container-fluid filter-form",
    )
    # https://django-crispy-forms.readthedocs.io/en/latest/crispy_tag_forms.html


class QueryForm(forms.Form):
    friendly_names = (("Prime Focus 1","Prime Focus 1 - 342"),
    ("Rcvr_800","Prime Focus 1 - 800"),
    ("Prime Focus 2","Prime Focus 2"),
    ("Rcvr1_2","L-Band"),
    ("Rcvr2_3","S-Band"),
    ("Rcvr4_6","C-Band"),
    ("Rcvr8_10","X-Band"),
    ("Rcvr12_18","Ku-Band"),
    ("RcvrArray18_26","KFPA"),
    ("Rcvr26_40","Ka-Band"),
    ("Rcvr40_52","Q-Band"))


    receivers = forms.MultipleChoiceField(
        choices= friendly_names, label="Receivers", required=True
    )
    receivers.widget.attrs.update(size=len(Frontend.objects.all()))
    freq_high = forms.FloatField(label="High Frequency", required=False,
      error_messages={'freq_low':"Freq_high is lower than freq_low"}, widget=forms.TextInput())
    freq_low = forms.FloatField(label="<hr> Low Frequency", required=False, error_messages={"too_low":"Your high is too low"}, widget=forms.TextInput())
    date = forms.DateField(label="<hr> Project Date", required=False, widget=forms.TextInput(attrs={"type":"date"}))
    start = forms.DateField(label="<hr> Start Date", required=False, widget=forms.TextInput(attrs={"type":"date"}))
    end = forms.DateField(label="End Date", required=False, widget=forms.TextInput(attrs={"type":"date"}))

    # method for cleaning the data
    def clean(self, num_of_pts=0):
      super().clean()

      low  = self.cleaned_data.get("freq_low")
      high = self.cleaned_data.get("freq_high")
      self.cleaned_data.get("receivers")
      date = self.cleaned_data.get("date")
      start = self.cleaned_data.get("start")
      end = self.cleaned_data.get("end")

      if low and high:
        if not float(low):
          self.add_error('freq_low', forms.ValidationError('Frequencies must be numerical'))
        if not float(high):
          self.add_error('freq_high', forms.ValidationError('Frequencies must be numerical'))

        if low == high:
          self.add_error('freq_low', forms.ValidationError('Frequencies cannot be the same'))
          self.add_error('freq_high', forms.ValidationError('Frequencies cannot be the same'))

        if low > high:
          self.add_error('freq_low', forms.ValidationError('Low Frequency must be less than High Frequency'))
          self.add_error('freq_high', forms.ValidationError('Low Frequency must be less than High Frequency'))

      if (end and not start) or (start and not end):
        self.add_error('start', forms.ValidationError('Specify a start and end date'))
        self.add_error('end', forms.ValidationError('Specify a start and end date'))
      if end and start:
        if end < start:
          self.add_error('start', forms.ValidationError('End date must be later than start date'))
          self.add_error('end', forms.ValidationError('End date must be later than start date'))
        if (end-start) > MAX_TIME_SPAN:
          self.add_error('start', forms.ValidationError('Max time span is 1 year.'))
          self.add_error('end', forms.ValidationError('Max time span is 1 year.'))

      if (date and start) or (date and end):
        self.add_error('start', forms.ValidationError('Specify a date of interest OR date range'))
        self.add_error('end', forms.ValidationError('Specify a date of interest OR date range'))
        self.add_error('date', forms.ValidationError('Specify a date of interest OR date range'))

      if not date and not start and not end:
        self.add_error('start', forms.ValidationError('Specify a date of interest OR date range'))
        self.add_error('end', forms.ValidationError('Specify a date of interest OR date range'))
        self.add_error('date', forms.ValidationError('Specify a date of interest OR date range'))

      return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = QueryFormHelper()
