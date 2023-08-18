print("Importing...")
from datetime import datetime, timedelta
import time
import argparse
import json

# import pandas as pd
import dask.dataframe as dd

import panel as pn
import holoviews as hv
import holoviews.operation.datashader as hd
from colorcet import cm
import multiprocessing

hv.extension("bokeh")


class Benchmark:
    def __init__(self, description=None, logger=None):
        self._initial_time = time.perf_counter()
        self._logger = logger if logger else print
        self.description = "Did stuff" if description is None else description

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        _end = time.perf_counter()
        total_time = _end - self._initial_time
        self._logger(f"{self.description} in {total_time:.3f} seconds ")


with open("./filters.json") as file:
    filters = json.load(file)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("full_data_path")
    args = parser.parse_args()
    return args.full_data_path


@pn.cache
def get_data(full_data_path):
    print("Reading parquet files into memory...")
    start = time.perf_counter()
    df = dd.read_parquet(
        full_data_path,
        # categories=["session", "frontend", "backend"],
        columns=["session", "frontend", "backend", "intensity", "frequency"],
        npartitions=multiprocessing.cpu_count(),
    )  # .sort_values("frequency")
    df.persist()
    print(f"Elapsed time: {time.perf_counter() - start}s")
    return df


full_data_path = parse_arguments()
dataset = get_data(full_data_path)
cmaps = ["fire", "rainbow4", "blues", "kbc"]  # color maps


with Benchmark("Generated widgets"):
    # Generate widgets
    cmap = pn.widgets.Select(
        value=cm["fire"], options={c: cm[c] for c in cmaps}, name="Color map"
    )
    plot_type = pn.widgets.Select(
        value="points", options={"Points": "points", "Curve": "curve"}, name="Plot Type"
    )
    session = pn.widgets.MultiChoice(
        value=[], options=filters["sessions"], name="Session"
    )
    frontend = pn.widgets.MultiSelect(
        value=[], options=filters["frontends"], name="Frontend"
    )
    backend = pn.widgets.MultiSelect(
        value=[], options=filters["backends"], name="Backend"
    )

widgets = [
    plot_type,
    cmap,
    session,
    frontend,
    backend,
]


@pn.depends(
    plot_type=plot_type,
    session=session,
    frontend=frontend,
    backend=backend,
)
def plot_points(
    plot_type,
    session,
    frontend,
    backend,
    **kwargs,
):
    """Filter dataframe based on widget values and generate Geoviews points"""
    print("Filtering data...")
    with Benchmark("Filtered data"):
        filtered = dataset
        if session:
            filtered = filtered[filtered["session"].isin(session)]
        if frontend:
            filtered = filtered[filtered["frontend"].isin(frontend)]
        if backend:
            filtered = filtered[filtered["backend"].isin(backend)]

        if plot_type == "curve":
            plot = hv.Curve(filtered, "frequency", ["intensity"])
        elif plot_type == "points":
            plot = hv.Points(filtered, ["frequency", "intensity"])
        else:
            raise ValueError(f"invalid {plot_type=}")
    return plot.opts(xlabel="Hz", ylabel="Jy")


@pn.depends(cmap, plot_type, session, frontend, backend)
def view(cmap, plot_type, session, frontend, backend, **kwargs):
    """Creates the plot that updates with widget values"""

    points = hv.DynamicMap(plot_points)
    with Benchmark("Rasterized"):
        agg = hd.rasterize(points, precompute=True)  # line_width=1 for curve
    with Benchmark("Shaded"):
        shaded = hd.shade(agg, cmap=cmap).opts(width=1200, height=800)
    # spread = hd.spread(shaded,px=1)
    with Benchmark("Spread"):
        spread = hd.dynspread(shaded, max_px=2, threshold=0.8)

    plot = spread.opts(
        tools=["box_select"],
        active_tools=["pan", "wheel_zoom"],
        xlabel="Frequency (MHz)",
        ylabel="Intensity (Jy)",
    )

    return plot


template = pn.template.FastListTemplate(
    title="RFI Data Interactive Dashboard",
    sidebar=[pn.pane.Markdown("All* RFI Data")] + widgets,
    logo="https://greenbankobservatory.org/wp-content/uploads/2019/10/GBO-Primary-HighRes-White.png",
    theme="dark",
)
template.main.append(pn.Column(view))
template.servable()

# to run:
# panel serve ant_pos_panel_server.py --allow-websocket-origin [address]
# --args [full data parquet] [metadata parquet]
