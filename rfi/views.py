
import datetime
import logging

import dateutil.parser as dp
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import plotly.offline as opy
from plotly.subplots import make_subplots
from scipy.signal import find_peaks

from django import forms
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.utils.timezone import make_aware
from django.views import View

from .forms import QueryForm
from .models import Frequency, Scan

logger = logging.getLogger(__name__)


def landing_page(request):
    # only call the query if the user submitted something.
    form = QueryForm()
    if request.method == "GET":
        if request.GET.get("submit") == "Submit":
            return query(request)

    return render(request, "rfi/query.html", {"form": form})

def query(request):
    # can set up as a single view with a sidebar for the query and a main block for the graph
    # should present each as an option, for the rif team
    # https://getbootstrap.com/docs/5.0/examples/sidebars/#
    form = QueryForm(request.GET)
    if form.is_valid():
        return DoGraph.as_view()(request)
    ## not passing on the keywords because there is no where for it to populate in the html...
    else: print("form is not valid!")

    return render(request, "rfi/query.html", {"form": form})

class DoGraph(View):
    def get(self, request):
        self.request = request
        self.get_data()
        channels = self.filter_data()
        div, refined_data = self.create_avg_line(channels)
        if div == None:
            return self.plot_it(div)
        else:
            div = self.create_color_plot(div, refined_data)
            return self.plot_it(div)

    def get_data(self):
        # clean the form
        if self.request.method == "GET":
            self.cache_form = QueryForm(self.request.GET)
            if self.cache_form.is_valid():
                print("passed inspection. querying now")

        # gather all the fields
        self.requested_receivers = self.request.GET.getlist("receivers")
        if "RcvrPF_1" in self.requested_receivers:
            self.requested_receivers.extend(["Prime Focus 1", "Rcvr_800"])

        self.requested_freq_low = self.request.GET.get("freq_low", None)
        self.requested_freq_high = self.request.GET.get("freq_high", None)

        self.requested_date = (
            make_aware(dp.parse(date_str))
            if (date_str := self.request.GET.get("date"))
            else None
        )

        self.requested_start = (
            make_aware(dp.parse(start_str))
            if (start_str := self.request.GET.get("start"))
            else None
        )
        self.requested_end = (
            make_aware(dp.parse(end_str))
            if (end_str := self.request.GET.get("end"))
            else None
        )

    def filter_data(self):
        # filter out non-relevant data
        channels = Frequency.objects.all().filter(scan__frontend__name__in=self.requested_receivers)
        # filter by the frequencies
        if self.requested_freq_low:
            channels = channels.filter(frequency__gte=float(self.requested_freq_low))
        if self.requested_freq_high:
            channels = channels.filter(frequency__lte=float(self.requested_freq_high))

        # then we can either use the nearest date or a date range
        scans = Scan.objects.filter(frontend__name__in=self.requested_receivers)
        if self.requested_date:
            # Get the nearest MJD (without scanning the whole table)
            try:
                self.nearest_date = (
                    scans.filter(datetime__lte=self.requested_date)
                    .order_by("-datetime")
                    .first()
                    .datetime
                )
                channels = channels.filter(scan__datetime=self.nearest_date)
            except:
                raise ValidationError(("No Data previous to your specified date."), code="NoDataInRange")

        elif self.requested_start or self.requested_end:
            if self.requested_start:
                channels = channels.filter(scan__datetime__gte=self.requested_start)
            if self.requested_end:
                channels = channels.filter(scan__datetime__lte=self.requested_end)

        else:
            most_recent_scan = scans.latest("datetime")
            channels = channels.filter(scan=most_recent_scan)


        # NOTE: Use this to decimate DURING the query. This will be a non-deterministic (but not quite random)
        #       sampling of every 10th row
        # channels = channels.annotate(mod=F("id") % 10).filter(mod=0)
        # channels = channels.order_by("scan__datetime", "channel")
        channels = channels.order_by("frequency")

        return channels

    def create_avg_line(self, channels):

        # check that we aren't querying too much even before find_peaks reduction
        refined_data = [] # this is just a placeholder if there is an error
        MAX_POINTS_TO_QUERY = 3_000_000
        print(channels.count())
        if channels.count() > MAX_POINTS_TO_QUERY:
            self.cache_form._errors["receivers"] = forms.ValidationError(f"Too many points queried by a factor of \
                ~{round(channels.count()/MAX_POINTS_TO_QUERY/2, 1)}. Please select smaller ranges.")
            div = None
            self.error_data_str = 'Maximum Data Queried - Reduce date or freq. ranges'
            return div, refined_data

        # set the prominence
        prom_by_rcvr = {
        "RcvrPF_1": 0.05,
        "Rcvr_800": 0.05,
        "Prime Focus 1": 0.05,
        "Prime Focus 2": 0.001,
        "Rcvr1_2": 0.03,
        "Rcvr2_3": 0.001,
        "Rcvr4_6": 0.001,
        "Rcvr8_10": 0.001,
        "Rcvr12_18": 0.001,
        "RcvrArray18_26": 0.001,
        "Rcvr26_40": 0.001,
        "Rcvr40_52": 0.0001,
        }

        proms=[]
        for rcvr in self.requested_receivers:
            proms.append(prom_by_rcvr[rcvr])
        prominence_val = min(proms)
        print(f"this is the prom val: {prominence_val}")

        # set up the data to be used
        data = pd.DataFrame(
            channels.values("frequency", "intensity", "scan__datetime", "scan__session__name")
            )

        if not data.empty:
            # Find local maxima (peaks) in intensities (second axis). This seems to reduce
            # the data by roughly a third, but doesn't throw away any spikes
            # prominence can reduce the data even further while preserving the peaks
            intensity_peaks = find_peaks(data.intensity, prominence=prominence_val)[0]
            #print(f"{data.intensity.head(10)} {intensity_peaks[:10]}")
            all_local_maximum_intensities = data[data.index.isin(intensity_peaks)]
            # NOTE: Can toggle this to make sure the shape stays the same
            MAX_POINTS_TO_PLOT = 550_000
            refined_data = all_local_maximum_intensities
            refined_data = refined_data.sort_values(by=["scan__session__name", "frequency"])
            if len(refined_data.index) > MAX_POINTS_TO_PLOT:
                self.cache_form._errors["receivers"] = forms.ValidationError(f"Too many points: {len(refined_data.index):,}. Must be <{MAX_POINTS_TO_PLOT:,}. Select smaller ranges.")
                div = None
                self.error_data_str = 'Maximum Data Queried - Reduce date or freq. ranges'
                return div, refined_data

            print(f"Actual # {len(refined_data.index)}")

            self.unique_days = refined_data.scan__datetime.unique()

            div=[]
            avg_calculation = refined_data.groupby("frequency", as_index=False)['intensity'].mean()
            avg_calculation = avg_calculation.assign(scan__session__name='Average')


            layout = self.make_the_layout(refined_data)
            # make the session line
            fig_session = px.line(refined_data, x="frequency", y="intensity", color="scan__session__name", labels={"scan__session__name":"Session"})
            fig_avg = px.line(avg_calculation, x="frequency", y="intensity", color="scan__session__name", labels={"scan__session__name":"Session"})
            fig_avg.update_traces(line_color="black")

            figure = go.Figure(data=fig_avg.data + fig_session.data, layout=layout)
            div.append(opy.plot(figure, output_type='div'))

        else:
            # set div none, then skip color plot
            div = None
            self.error_data_str = 'No Data - Check date or freq. ranges'
            self.plot_it(div)

        return div, refined_data

    def create_color_plot(self, div, refined_data):
        # make the color plot/s and add them to div
        session = 1
        [str(i.date()) for i in self.unique_days]
        fig = make_subplots(rows=len(self.unique_days), cols=1, shared_xaxes=True, x_title="Frequency (MHz)")

        for self.unique_day in self.unique_days:
            date_of_interest_datetime = self.unique_day.to_pydatetime()

            unique_date_range = refined_data[
                refined_data["scan__datetime"] == date_of_interest_datetime
            ]  # get the data but only for one session of interest at a time
            date_of_interest_datetime = date_of_interest_datetime.replace(tzinfo=None)
            # make the date bins for plotting
            widen = datetime.timedelta(hours=1)
            date_bins = np.arange(
                date_of_interest_datetime - widen,
                date_of_interest_datetime + widen,
                datetime.timedelta(hours=1),
            ).astype(datetime.datetime)
            # Get the center of the date bins (for plotting)
            dates = date_bins[:-1] + 0.5 * np.diff(date_bins)
            # Convert from datetime
            mdates.date2num(dates)

            # make the freq bins for plotting
            freq_bins = np.arange(
                unique_date_range["frequency"].min(),
                unique_date_range["frequency"].max(),
                1.0,
            )

            # Get the center of the frequency bins (for plotting)
            freqs = freq_bins[:-1] + 0.5 * np.diff(freq_bins)

            df_rfi_grouped2 = unique_date_range.groupby(
                [
                    pd.cut(unique_date_range.scan__datetime, date_bins),
                    pd.cut(unique_date_range.frequency, freq_bins),
                ]
            )

            timeseries_rfi = df_rfi_grouped2.max().intensity

            to_plot = np.log10(timeseries_rfi.unstack())

            fig.append_trace(go.Heatmap(
                x=freq_bins,
                y=[str(self.unique_day.date())],
                z=to_plot,
                colorscale='Viridis',
                coloraxis="coloraxis", connectgaps = True,
                ), row=session, col=1,
                )

            session=session+1
            title_color = "RFI Environment at Green Bank Observatory per Session <br> <i>%s    %s    %s MHz</i>" % (self.date_range_str, self.rcvr_str, self.freq_range_str)
            layout = go.Layout(
                title=title_color,
                title_x=0.5,
                coloraxis = {'colorscale':'viridis'},
                height = 100+100*session-1
                )
            fig.update_layout(layout)
            fig.update_yaxes(tickformat="%b %d %Y", dtick=86400000)

        div.append(opy.plot(fig, auto_open=False, output_type="div"))
        return div

    def make_the_layout(self, refined_data):
        # make the layout
        start = refined_data["scan__datetime"].min()
        end = refined_data["scan__datetime"].max()
        if start == end:
            self.date_range_str = start.date()
        else:
            self.date_range_str = (
                f"{start.date()} - "
                f"{end.date()}"
            )
        self.freq_range_str = f'{refined_data["frequency"].min():.2f}-{refined_data["frequency"].max():.2f}'
        rcvr_names = {
            "RcvrPF_1": "PF1",
            "Prime Focus 2": "PF2",
            "Rcvr1_2": "L-Band",
            "Rcvr2_3": "S-Band",
            "Rcvr4_6": "C-Band",
            "Rcvr8_10": "X-Band",
            "Rcvr12_18": "Ku-Band",
            "RcvrArray18_26": "KFPA",
            "Rcvr26_40": "Ka-Band",
            "Rcvr40_52": "Q-Band",
            }

        requested_receivers_name=[rcvr_names[i] for i in self.requested_receivers if i not in ["Prime Focus 1", "Rcvr_800"]]
        self.rcvr_str = ", ".join(requested_receivers_name)

        title_line = "RFI Environment at Green Bank Observatory <br> <i>%s    %s    %s MHz</i>" % (self.date_range_str, self.rcvr_str, self.freq_range_str)
        layout = go.Layout(
            title=title_line,
            title_x=0.5,
            xaxis={"title": "Frequency (MHz)"},
            yaxis={"title": "Intensity (Jy)"},
        )

        return layout

    def plot_it(self, div):
        if div:
            return render(self.request, "rfi/query.html", {"graphs": div, "form": self.cache_form})
        else:
            # catch all the posibilities of bad data
            if self.requested_start:
                self.cache_form._errors["start"] = forms.ValidationError(self.error_data_str)
                self.cache_form._errors["end"] = forms.ValidationError(self.error_data_str)
            if self.requested_freq_low or self.requested_freq_low:
                self.cache_form._errors["freq_low"] = forms.ValidationError(self.error_data_str)
                self.cache_form._errors["freq_high"] = forms.ValidationError(self.error_data_str)
            return render(self.request, "rfi/query.html", {"form": self.cache_form})
