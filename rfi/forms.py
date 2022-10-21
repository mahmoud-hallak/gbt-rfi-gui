from django import forms

from rfi.models import Frontend


def check_size(value):
  if len(value) < 10:
    raise forms.ValidationError("bad freq low")

def check_rcvr(value):
  if value != "Rcvr2_3":
    raise forms.ValidationError("yucky rcvr")

class QueryForm(forms.Form):
    receivers = forms.ModelMultipleChoiceField(
        queryset=Frontend.objects.all(), label="Receivers", required=True,
    )
    freq_high = forms.FloatField(label="Frequency (MHz)", required=False,
      error_messages={'freq_low':"Freq_high is lower than freq_low"})
    freq_low = forms.FloatField(label="Frequency (MHz)", required=False)
    date = forms.DateField(label="Date", required=False)
    start = forms.DateField(label="Start", required=False)
    end = forms.DateField(label="End", required=False)

    # method for cleaning the data
    def clean(self):
      super(UserForm, self).clean()

      # getting username and password from cleaned_data
      low = self.cleaned_data.get('freq_low')
      rcvr = self.cleaned_data.get('receivers')

      # validating the username and password
      if len(low) < 3:
         self._errors['freq_low'] = self.error_class(['A minimum of 3 characters is required'])

      if rcvr != "Rcvr2_3":
         self._errors['receivers'] = self.error_class(['Use S-band'])

      return self.cleaned_data
