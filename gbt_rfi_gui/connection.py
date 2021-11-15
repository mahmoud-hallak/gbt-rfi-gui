import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mjd import datetime_to_mjd

# from .mjd import datetime_to_mjd, mjd_to_datetime

LOGGER = logging.getLogger(__name__)


def broad_plot(rfi):
    rfi_sorted = rfi.sort_values("frequency_mhz")
    valuex = rfi_sorted["frequency_mhz"]
    valuey = rfi_sorted["intensity_mean"]
    width1 = 9
    height1 = 4
    width_height_1 = (width1, height1)

    fig = plt.figure(figsize=width_height_1)
    plt.xlabel("Frequency MHz")
    plt.ylabel("Average Intensity Jy")
    plt.title("Average Intensity over specified Time")
    plt.plot(valuex, valuey, color="black", linewidth=0.5)
    plt.show()


def rms_plot(rfi):
    rfi["frequency_mhz"]
    rfi["intensity_mean"]
    width1 = 6
    height1 = 2
    width_height_1 = (width1, height1)

    fig = plt.figure(figsize=width_height_1)


def pick_range(rfi, start, stop):
    rfi.sort_values("frequency_mhz")
    frequency = rfi.sort_values["frequency_mhz"]
    intensity = rfi.sort_values["intensity_mean"]
    width1 = 9
    height1 = 4
    width_height_1 = (width1, height1)

    desired_range = frequency.between(start, stop, inclusive=True)
    values_listx = []
    values_listy = []

    for i in range(len(frequency)):
        if desired_range[i] == True:
            values_listx.append(frequency[i])
            values_listy.append(intensity[i])
        else:
            None

    plt.figure(1)
    fig = plt.figure(figsize=width_height_1)
    plt.xlabel("Frequency MHz")
    plt.ylabel("Intensity Jy")
    plt.title("RFI Environment at Green Bank Observatory")
    plt.plot(values_listx, values_listy, color="black", linewidth=0.5)
    plt.show()


def color_plot(df, receiver, time1, time2):

    df_rfi = df
    mjd1 = datetime_to_mjd(time1)
    mjd2 = datetime_to_mjd(time2)
    freq_bins = np.arange(df_rfi.frequency_mhz.min(), df_rfi.frequency_mhz.max(), 1.0)
    # Get the center of the frequency bins (for plotting)
    freqs = freq_bins[:-1] + 0.5 * np.diff(freq_bins)

    abs(mjd1 - mjd2)
    # abs_mjd = 4
    mjd_bins = np.arange(df_rfi.mjd.min(), df_rfi.mjd.max(), 1)
    # Get the center of the MJD bins (for plotting)
    mjds = mjd_bins[:-1] + 0.5 * np.diff(mjd_bins)

    df_rfi_grouped2 = df_rfi.groupby(
        [pd.cut(df_rfi.mjd, mjd_bins), pd.cut(df_rfi.frequency_mhz, freq_bins)]
    )
    print(df_rfi_grouped2)

    timeseries_rfi = df_rfi_grouped2.max().intensity_jy

    # plt.figure(2)
    fig = plt.figure(figsize=(10.5, 7))
    ax = fig.gca()
    im = ax.imshow(
        np.log10(timeseries_rfi.unstack()),
        origin="lower",
        aspect="auto",
        extent=(freqs[0], freqs[-1], mjds[0], mjds[-1]),
        interpolation="none",
    )

    cbar = fig.colorbar(im)
    ax.get_yaxis().get_major_formatter().set_useOffset(False)
    ax.set_xlabel("freq (MHz)")
    ax.set_ylabel("mjd")

    cbar.set_label("log(flux) [Jy]")
    ax.set_title("RFI Color Plot")
    fig.savefig("max_spectrum_vs_time_2d.png", dpi=300)
    plt.show()
