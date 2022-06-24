import logging
from datetime import timedelta

import dateutil.parser as dp
import numpy as np
import plotly.graph_objs as go
import plotly.offline as opy
from scipy.signal import find_peaks

from django.db.models import FloatField, Max, Min
from django.db.models.functions import Cast
from django.shortcuts import redirect, render
from django.utils.timezone import make_aware

from .forms import QueryForm
from .models import Frequency, Frontend, Scan

logger = logging.getLogger(__name__)

MAX_TIME_SPAN = timedelta(days=70)


def query(request):
    form = QueryForm()
    return render(request, "rfi/query.html", {"form": form})


def graph(request):
    print(request.GET)
    channels = Frequency.objects.all()

    Frontend.objects.all()
    requested_receivers = request.GET.getlist("receivers")
    if requested_receivers:
        channels = channels.filter(scan__frontend__name__in=requested_receivers)
        print(f"Filtering channels to those taken with {requested_receivers=}")

    requested_freq_low = request.GET.get("freq_low", None)
    if requested_freq_low:
        # TODO: handle errors
        channels = channels.filter(frequency__gte=float(requested_freq_low))
        print(f"Filtering channels to those taken above {requested_freq_low=}MHz")
    requested_freq_high = request.GET.get("freq_high", None)
    if requested_freq_high:
        # TODO: handle errors
        channels = channels.filter(frequency__lte=float(requested_freq_high))
        print(f"Filtering channels to those taken below {requested_freq_high=}MHz")

    # TODO: handle errors
    requested_date = (
        make_aware(dp.parse(date_str))
        if (date_str := request.GET.get("date"))
        else None
    )
    # TODO: handle errors
    requested_start = (
        make_aware(dp.parse(start_str))
        if (start_str := request.GET.get("start"))
        else None
    )
    # TODO: handle errors
    requested_end = (
        make_aware(dp.parse(end_str)) if (end_str := request.GET.get("end")) else None
    )
    if requested_end and requested_start:
        if requested_end < requested_start:
            raise ValueError(
                f"End ({requested_end}) can't be before start ({requested_start})"
            )
        if requested_end - requested_start > MAX_TIME_SPAN:
            raise ValueError(
                f"Specify a reasonable start/end range (less than {MAX_TIME_SPAN})"
            )

    scans = Scan.objects.filter(frontend__name__in=requested_receivers)
    if requested_date:
        # Get the nearest MJD (without scanning the whole table)
        nearest_date = (
            scans.filter(datetime__lte=requested_date)
            .order_by("-datetime")
            .first()
            .datetime
        )
        channels = channels.filter(scan__datetime=nearest_date)
        print(f"Filtering channels to those taken in nearest scan {nearest_date}")

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
    MAX_POINTS_TO_PLOT = 500_000
    if (num_channels := channels.count()) > MAX_POINTS_TO_PLOT:
        raise ValueError(
            f"Too many points: {num_channels:,}. Must be <{MAX_POINTS_TO_PLOT:,}"
        )
    data = channels.annotate(
        freq_float=Cast("frequency", FloatField()),
        intensity_float=Cast("intensity", FloatField()),
    ).values_list("freq_float", "intensity_float")
    print(f"Plotting {len(data)} points")
    if data.exists():
        freq_vs_intensity = np.array(data)
        # Find local maxima (peaks) in intensities (second axis). This seems to reduce
        # the data by roughly a third, but doesn't throw away any spikes
        intensity_peaks = find_peaks(freq_vs_intensity[:,1])[0]
        all_local_maximum_intensities = freq_vs_intensity[intensity_peaks]
        # NOTE: Can toggle this to make sure the shape stays the same
        # to_plot = freq_vs_intensity
        to_plot = all_local_maximum_intensities
        print(f"Actual # {len(to_plot)}")
        graph = go.Scatter(
            x=to_plot[:,0],
            y=to_plot[:,1],
            marker={"color": "red", "symbol": "circle", "size": 3},
            # mode="markers",
            name="1st Trace",
        )
        if start == end:
            date_range_str = start.strftime("%Y/%m/%d %H:%M:%S")
        else:
            date_range_str = (
                f"{start.strftime('%Y/%m/%d %H:%M:%S')} - "
                f"{end.strftime('%Y/%m/%d %H:%M:%S')}"
            )
        layout = go.Layout(
            title=f"RFI Data ({date_range_str})",
            xaxis={"title": "Frequency (MHz)"},
            yaxis={"title": "Intensity (Jy)"},
        )
        figure = go.Figure(data=graph, layout=layout)
        div = opy.plot(figure, auto_open=False, output_type="div")
    else:
        div = None

    if div:
        return render(request, "rfi/graph.html", {"graph": div})
    else:
        return redirect("/query")
