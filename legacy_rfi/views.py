from datetime import timedelta

import numpy as np

from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

import plotly.offline as opy
import plotly.graph_objs as go

from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

import dateutil.parser as dp
from django.db.models import CharField, FloatField
from django.db.models.functions import Cast
from legacy_rfi.models import MasterRfiCatalog
from .mjd import datetime_to_mjd, mjd_to_datetime

from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

from .forms import QueryForm


def query(request):
    form = QueryForm()
    return render(request, "rfi/query.html", {"form": form})


def graph(request):
    rows = MasterRfiCatalog.objects.all()
    receivers = request.GET.getlist("receivers")
    if receivers:
        rows = rows.filter(frontend__in=receivers)

    freq_low = request.GET.get("freq_low", None)
    freq_high = request.GET.get("freq_high", None)
    if freq_low:
        rows = rows.filter(frequency_mhz__gte=float(freq_low))
    if freq_high:
        rows = rows.filter(requency_mhz__lte=float(freq_high))
    date = dp.parse(date_str) if (date_str := request.GET.get("date")) else None
    start = dp.parse(start_str) if (start_str := request.GET.get("start")) else None
    end = dp.parse(end_str) if (end_str := request.GET.get("end")) else None
    if not start or not end or end - start > timedelta(days=7):
        raise ValueError("Specify a reasonable start/end range (<1 week)")
    if date:
        date_mjd = datetime_to_mjd(date)
        # Get the nearest MJD (without scanning the whole table)
        mjd = max(
            abs(mjd_)
            for mjd_ in (
                rows.filter(mjd__gte=date_mjd)
                .order_by("mjd")[:1]
                .union(rows.filter(mjd__lt=date_mjd).order_by("-mjd")[:1])
                .values_list("mjd", flat=True)
            )
        )
        print(
            "Using nearest MJD value {} ({}) to given date {} ({})".format(
                mjd, mjd_to_datetime(mjd), date_mjd, date
            )
        )
        rows = rows.filter(mjd=mjd)
        start_mjd = mjd
        end_mjd = mjd
    elif start or end:
        start_mjd = datetime_to_mjd(start)
        end_mjd = datetime_to_mjd(end)
        if start:
            print("Selecting scans starting after {}".format(start_mjd))
            rows = rows.filter(mjd__gte=start_mjd)
        if end:
            print("Selecting scans starting before {}".format(end_mjd))
            rows = rows.filter(mjd__lte=end_mjd)
    else:
        print("calc max")
        mjd = rows.aggregate(Max("mjd"))["mjd__max"]
        print("Using latest MJD value {} ({})".format(mjd, mjd_to_datetime(mjd)))
        rows = rows.filter(mjd=mjd)
        start_mjd = mjd
        end_mjd = mjd

    data = rows.annotate(
        freq_str=Cast("frequency_mhz", FloatField()),
        intensity_str=Cast("intensity_jy", FloatField()),
    ).values_list("freq_str", "intensity_str")[:100]

    if data.exists():
        transposed = np.array(list(zip(*data)))
        data = go.Scatter(
            x=transposed[0][::2],
            y=transposed[1][::2],
            marker={"color": "red", "symbol": 104, "size": 10},
            mode="lines",
            name="1st Trace",
        )
        start_dt = mjd_to_datetime(start_mjd)
        end_dt = mjd_to_datetime(end_mjd)
        date_range_str = (
            f"{start_dt.strftime('%Y/%m/%d %H:%M:%S')} - "
            f"{end_dt.strftime('%Y/%m/%d %H:%M:%S')}"
        )
        layout = go.Layout(
            title=f"RFI Data ({date_range_str})",
            xaxis={"title": "Frequency (MHz)"},
            yaxis={"title": "Intensity (Jy)"},
        )
        figure = go.Figure(data=data, layout=layout)
        div = opy.plot(figure, auto_open=False, output_type="div")
    else:
        div = None

    if div:
        return render(request, "rfi/graph.html", {"graph": div})
    else:
        return redirect("/query")
