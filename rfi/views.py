
import datetime
import logging

import dateutil.parser as dp
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.offline as opy
from plotly.subplots import make_subplots
from scipy.signal import find_peaks

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import FloatField, Max, Min
from django.db.models.functions import Cast
from django.shortcuts import render
from django.utils.timezone import make_aware

from .forms import QueryForm
from .models import Frequency, Frontend, Scan

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
        return graph(request)
    ## not passing on the keywords because there is no where for it to populate in the html...
    else: print("form is not valid!")

    return render(request, "rfi/query.html", {"form": form})

def graph(request):
    if request.method == "GET":
        cache_form = QueryForm(request.GET)
        if cache_form.is_valid():
            print("passed inspection. querying now")

    print(request.GET)
    channels = Frequency.objects.all()

    Frontend.objects.all()
    requested_receivers = request.GET.getlist("receivers")

    if requested_receivers:
        channels = channels.filter(scan__frontend__name__in=requested_receivers)
        print(f"Filtering channels to those taken with {requested_receivers=}")

    requested_freq_low = request.GET.get("freq_low", None)
    requested_freq_high = request.GET.get("freq_high", None)

    if requested_freq_low and requested_freq_high:
        try:
            requested_freq_high = float(requested_freq_high)
            requested_freq_low = float(requested_freq_low)
        except:
            raise ValidationError(_("Frequencies are not float numbers."), code="NonFloatFreq")
        if requested_freq_low == requested_freq_high:
            raise ValidationError("Requested Frequency High is the same as the requested low", code="HighSameAsLow")
        channels = channels.filter(frequency__gte=float(requested_freq_low))
        print(f"Filtering channels to those taken above {requested_freq_low=}MHz")
        channels = channels.filter(frequency__lte=float(requested_freq_high))
        print(f"Filtering channels to those taken below {requested_freq_high=}MHz")
    else:
        if requested_freq_low:
            try: requested_freq_low = float(requested_freq_low)
            except: raise ValidationError("Low frequency is not a float number.", code="NonFloatLowFreq")
            channels = channels.filter(frequency__gte=float(requested_freq_low))
            print(f"Filtering channels to those taken above {requested_freq_low=}MHz")
        if requested_freq_high:
            try: requested_freq_high = float(requested_freq_high)
            except: raise ValidationError("High frequency is not a float number.", code="NonFloatHighFreq")
            channels = channels.filter(frequency__lte=float(requested_freq_high))
            print(f"Filtering channels to those taken below {requested_freq_high=}MHz")

    requested_date = (
        make_aware(dp.parse(date_str))
        if (date_str := request.GET.get("date"))
        else None
    )

    requested_start = (
        make_aware(dp.parse(start_str))
        if (start_str := request.GET.get("start"))
        else None
    )
    requested_end = (
        make_aware(dp.parse(end_str)) if (end_str := request.GET.get("end")) else None
    )
    if requested_end and requested_start:
        if requested_end < requested_start:
            raise ValidationError(
                "End %(requested_end) can't be before start %(requested_start)", params={'requested_end':requested_end, 'requested_start':requested_start}, code="EndDateBeforeStart"
            )

    scans = Scan.objects.filter(frontend__name__in=requested_receivers)
    if requested_date:
        # Get the nearest MJD (without scanning the whole table)
        try:
            nearest_date = (
                scans.filter(datetime__lte=requested_date)
                .order_by("-datetime")
                .first()
                .datetime
            )
            channels = channels.filter(scan__datetime=nearest_date)
            print(f"Filtering channels to those taken in nearest scan {nearest_date}")
        except:
            raise ValidationError(_("No Data previous to your specified date."), code="NoDataInRange")

    elif requested_start or requested_end:
        if requested_start:
            print(
                f"Filtering channels to those in scans starting after {requested_start}"
            )
            channels = channels.filter(scan__datetime__gte=requested_start)
        if requested_end:
            print(
                f"Filtering channels to those in scans starting before {requested_end}"
            )
            channels = channels.filter(scan__datetime__lte=requested_end)

    else:
        most_recent_scan = scans.latest("datetime")
        channels = channels.filter(scan=most_recent_scan)
        print(
            f"Filtering channels to those taken in most recent scan {most_recent_scan.datetime}"
        )

    # NOTE: Use this to decimate DURING the query. This will be a non-deterministic (but not quite random)
    #       sampling of every 10th row
    # channels = channels.annotate(mod=F("id") % 10).filter(mod=0)
    # channels = channels.order_by("scan__datetime", "channel")
    channels = channels.order_by("frequency")

    channel_aggregates = (
        channels.values("scan__datetime")
        .distinct()
        .aggregate(
            last_scan_start=Max("scan__datetime"),
            first_scan_start=Min("scan__datetime"),
        )
    )
    start = channel_aggregates["first_scan_start"]
    end = channel_aggregates["last_scan_start"]

    # set the prominence
    prom_by_rcvr = {
    "Prime Focus 1": 0.17,
    "Rcvr_800": 0.17,
    "Prime Focus 2": 0.17,
    "Rcvr1_2": 10,
    "Rcvr2_3": 0.17,
    "Rcvr4_6": 0.17,
    "Rcvr8_10": 0.17,
    "Rcvr12_18": 0.17,
    "RcvrArray18_26": 0.17,
    "Rcvr26_40": 0.17,
    "Rcvr40_52": 0.17,
    }

    proms=[]
    for rcvr in requested_receivers:
        proms.append(prom_by_rcvr[rcvr])
    prominence_val = max(proms)
    print(f"this is the prom val: {prominence_val}")

    data = channels.annotate(
        freq_float=Cast("frequency", FloatField()),
        intensity_float=Cast("intensity", FloatField()),
    ).values_list("freq_float", "intensity_float")
    print(f"Plotting {len(data)} points")
    if data.exists():
        freq_vs_intensity = np.array(data)
        # Find local maxima (peaks) in intensities (second axis). This seems to reduce
        # the data by roughly a third, but doesn't throw away any spikes
        # prominence can reduce the data even further while preserving the peaks
        intensity_peaks = find_peaks(freq_vs_intensity[:,1])[0]#, prominence=prominence_val)[0]
        all_local_maximum_intensities = freq_vs_intensity[intensity_peaks]
        # NOTE: Can toggle this to make sure the shape stays the same
        # to_plot = freq_vs_intensity
        MAX_POINTS_TO_PLOT = 750_000
        to_plot = all_local_maximum_intensities
        if len(to_plot) > MAX_POINTS_TO_PLOT:
            cache_form._errors["receivers"] = forms.ValidationError(f"Too many points: {len(to_plot):,}. Must be <{MAX_POINTS_TO_PLOT:,}. Select smaller ranges.")
            return render(request, "rfi/query.html", {"form": cache_form})

        print(f"Actual # {len(to_plot)}")

        # set up the data to be used
        data = pd.DataFrame(
            channels.values("frequency", "intensity", "scan__datetime", "scan__session__name")
            )

        data = data.sort_values(by=['scan__datetime'])
        unique_days = data.scan__datetime.unique()

        div=[]

        # create the line plot and add it to div
        graph = go.Scatter(
            x=to_plot[:,0],
            y=to_plot[:,1],
            marker={"color": "black", "symbol": "circle", "size": 3},
        )
        if start == end:
            date_range_str = start.strftime("%m/%d/%Y")
        else:
            date_range_str = (
                f"{start.strftime('%m/%d/%Y')} - "
                f"{end.strftime('%m/%d/%Y')}"
            )
        freq_range_str = f"{data.frequency.min():.2f}-{data.frequency.max():.2f}"
        rcvr_names = {
            "Prime Focus 1": "PF1",
            "Rcvr_800": "PF1_800",
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
        requested_receivers_name=[rcvr_names[i] for i in requested_receivers]
        rcvr_str = ", ".join(requested_receivers_name)
        title_line = "Averaged RFI Environment at Green Bank Observatory <br> <i>%s    %s    %s MHz</i>" % (date_range_str, rcvr_str, freq_range_str)
        layout = go.Layout(
            title=title_line,
            title_x=0.5,
            xaxis={"title": "Frequency (MHz)"},
            yaxis={"title": "Intensity (Jy)"},
        )
        figure = go.Figure(data=graph, layout=layout)
        div.append(opy.plot(figure, auto_open=False, output_type="div"))


        # make the color plot/s and add them to div
        session = 1
        [str(i.date()) for i in unique_days]
        fig = make_subplots(rows=len(unique_days), cols=1, shared_xaxes=True, x_title="Frequency (MHz)")

        for unique_day in unique_days:
            date_of_interest_datetime = unique_day.to_pydatetime()

            unique_date_range = data[
                data["scan__datetime"] == date_of_interest_datetime
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
                y=[str(unique_day.date())],
                z=to_plot,
                colorscale='Viridis',
                coloraxis="coloraxis"
                ), row=session, col=1,
                )

            session=session+1
            title_color = "RFI Environment at Green Bank Observatory per Session <br> <i>%s    %s    %s MHz</i>" % (date_range_str, rcvr_str, freq_range_str)
            layout = go.Layout(
                title=title_color,
                title_x=0.5,
                coloraxis = {'colorscale':'viridis'},
                height = 100+100*session-1
                )
            fig.update_layout(layout)
            fig.update_yaxes(tickformat="%b %d %Y", dtick=86400000)

        div.append(opy.plot(fig, auto_open=False, output_type="div"))

    else:
        div = None

    if div:
        return render(request, "rfi/query.html", {"graphs": div, "form": cache_form})
    else:
        cache_form._errors["start"] = forms.ValidationError('No Data in selected range')
        cache_form._errors["end"] = forms.ValidationError('No Data in selected range')
        return render(request, "rfi/query.html", {"form": cache_form})
