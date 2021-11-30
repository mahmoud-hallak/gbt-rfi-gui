import datetime
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rfi_query.settings")

import django

django.setup()

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytz
from PyQt5 import QtGui, QtWidgets
from PyQt5.Qt import QMainWindow
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.uic import loadUiType

from rfi.models import Frequency, Frontend, Scan

# add .Ui file path here
qtCreatorFile = (
    "/home/sandboxes/kpurcell/repos/RFI_GUI/gbt_rfi_query/gbt_rfi_gui/RFI_GUI.ui"
)
Ui_MainWindow, QtBaseClass = loadUiType(qtCreatorFile)


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        # Set up the UI file
        self.setupUi(self)

        # to protect teh database use only a time range of 30 days
        self.MAX_TIME_RANGE = datetime.timedelta(days=30)

        # List of receivers
        self.receivers.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.receivers.addItems(list(Frontend.objects.values_list("name", flat=True)))

        # Start and Stop Date DateEdit widgets
        self.target_date.setDate(datetime.datetime.today())

        # Frequency Range
        self.start_frequency.setValidator(QtGui.QDoubleValidator())
        self.end_frequency.setValidator(QtGui.QDoubleValidator())

        # Push Button to get data
        self.plot_button.clicked.connect(self.clicked)

        # connect menus
        self.actionQuit.triggered.connect(self.menuQuit)
        self.actionAbout.triggered.connect(self.menuAbout)

    def get_scans(self, receivers, target_date, start_frequency, end_frequency):
        # don't want to look at dates with no data, find the most recent session date
        most_recent_session_prior_to_target_datetime = (
            Scan.objects.filter(datetime__lte=target_date)
            .order_by("-datetime")
            .first()
            .session
        )
        # only care about the most recent session before the target date,
        #    we dont want to poll all scans
        qs = Scan.objects.filter(
            scan__session=most_recent_session_prior_to_target_datetime
        )

        if receivers:
            print(f"Filtering by {receivers=}")
            qs = qs.filter(frontend__name__in=receivers)

        if target_date:
            print(f"Filtering by {target_date=}")
            print(
                f"Starting from {(target_date-self.MAX_TIME_RANGE).date()=} to {target_date.date()=}"
            )
            qs = qs.filter(datetime__gte=target_date - self.MAX_TIME_RANGE)
            qs = qs.filter(datetime__lte=target_date)

        if start_frequency:
            print(f"Filtering by {start_frequency=}")
            qs = qs.filter(frequency__frequency__gte=start_frequency)

        if end_frequency:
            print(f"Filtering by {end_frequency=}")
            qs = qs.filter(frequency__frequency__lte=end_frequency)

        return qs

    def do_plot(self, receivers, target_date, start_frequency, end_frequency):
        # don't want to look at dates with no data, find the most recent session date
        most_recent_session_prior_to_target_datetime = (
            Scan.objects.filter(datetime__lte=target_date)
            .order_by("-datetime")
            .first()
            .datetime
        )

        print(
            f"Most recent session date: {most_recent_session_prior_to_target_datetime.date()}"
        )

        qs = Frequency.objects.all()

        if receivers:
            print(f"Filtering by {receivers=}")
            qs = qs.filter(scan__frontend__name__in=receivers)

        if target_date:
            # if there is no data shift the range to a month with the most recent data
            if (
                target_date - self.MAX_TIME_RANGE
                > most_recent_session_prior_to_target_datetime
            ):
                target_date = most_recent_session_prior_to_target_datetime
            print(f"Filtering by {target_date.date()=}")
            print(
                f"Starting from {(target_date-self.MAX_TIME_RANGE).date()} to {target_date.date()}"
            )
            qs = qs.filter(scan__datetime__gte=target_date - self.MAX_TIME_RANGE)
            qs = qs.filter(scan__datetime__lte=target_date)

        if start_frequency:
            print(f"Filtering by {start_frequency=}")
            qs = qs.filter(frequency__gte=start_frequency)

        if end_frequency:
            print(f"Filtering by {end_frequency=}")
            qs = qs.filter(frequency__lte=end_frequency)

        # make a 3 column dataFrame for the data needed to plot
        data = pd.DataFrame(qs.values("frequency", "intensity", "scan__datetime"))

        # make a new object with the average intensity for the 2D plot
        mean_data_intens = data.groupby(["scan__datetime", "frequency"]).agg(
            {"intensity": ["mean"]}
        )
        mean_data_intens.columns = ["intensity_mean"]
        mean_data = mean_data_intens.reset_index()
        # sort values with respect to x axis so the plot looks better, this has nothing to do with the data
        mean_data.sort_values(by=["frequency"])

        if not data.empty:
            # Plot the 2D graph
            plt.figure(figsize=(9, 4))
            plt.title("Averaged RFI Environment at Green Bank Observatory")
            plt.xlabel("Frequency MHz")
            plt.ylabel("Average Intensity Jy")
            plt.plot(
                mean_data["frequency"],
                mean_data["intensity_mean"],
                color="black",
                linewidth=0.5,
            )
            plt.show()

            # Plot the color map graph, but only if there is more than one day with data
            self.make_color_plot(data)

            # option to save the data from the plot
            if self.saveData.isChecked():
                self.save_file(
                    pd.DataFrame(qs.values("scan__datetime", "frequency", "intensity"))
                )

        else:
            QtWidgets.QMessageBox.information(
                self,
                "No Data Found",
                "There is no data for the given filters",
                QtWidgets.QMessageBox.Ok,
            )

    def make_color_plot(self, data):
        freq_bins = np.arange(data["frequency"].min(), data["frequency"].max(), 1.0)
        # Get the center of the frequency bins (for plotting)
        freqs = freq_bins[:-1] + 0.5 * np.diff(freq_bins)

        # arrange will clip off the beginning and end time data unless there is an offset
        # only technically need one day but 2 makes the plot look better
        #    also need additional functions to work with datetime
        widen_range_of_bins = datetime.timedelta(days=2)
        date_bins = np.arange(
            data.scan__datetime.min() - widen_range_of_bins,
            data.scan__datetime.max() + widen_range_of_bins,
            datetime.timedelta(days=1),
        ).astype(datetime.datetime)
        # Get the center of the date bins (for plotting)
        dates = date_bins[:-1] + 0.5 * np.diff(date_bins)
        # Convert from datetime so imshow recignizes the extent format
        date_extents = mdates.date2num(dates)

        df_rfi_grouped2 = data.groupby(
            [pd.cut(data.scan__datetime, date_bins), pd.cut(data.frequency, freq_bins)]
        )

        timeseries_rfi = df_rfi_grouped2.max().intensity

        # plt.figure(2)
        fig = plt.figure(figsize=(10.5, 7))
        ax = fig.gca()
        im = ax.imshow(
            np.log10(timeseries_rfi.unstack()),
            origin="lower",
            aspect="auto",
            extent=(freqs[0], freqs[-1], date_extents[0], date_extents[-1]),
            interpolation="none",
        )

        cbar = fig.colorbar(im)
        ax.get_yaxis().get_major_formatter().set_useOffset(False)
        ax.set_xlabel("freq (MHz)")
        ax.set_ylabel("dates")

        cbar.set_label("log(flux) [Jy]")
        ax.set_title("RFI Environment at Green Bank Observatory per Session")
        # convert the date extents back into datetime
        ax.yaxis_date()
        plt.show()

    def save_file(self, data):
        name, filetype = QFileDialog.getSaveFileName(
            self, "Save File"
        )  # get the name from fancy QFileDialog
        if name:
            # don't abort if user cancels save
            data.to_csv(f"{name}.csv")
            print(f"{name}.csv file was saved")

    def menuAbout(self):
        """Shows about message box."""
        QMessageBox.about(
            self,
            "gbt_rfi_gui",
            "gbt_rfi_gui information here",
        )

    def menuQuit(self):
        """Method to handle the quit menu."""
        print("Thanks for using the gbt_rfi_gui")
        sys.exit()

    def clicked(self):
        receivers = [i.text() for i in self.receivers.selectedItems()]
        target_date = (
            self.target_date.dateTime().toPyDateTime().replace(tzinfo=pytz.UTC)
        )

        try:
            start_frequency = float(self.start_frequency.text())
        except ValueError:
            start_frequency = None
            self.start_frequency.setText("")

        try:
            end_frequency = float(self.end_frequency.text())
        except ValueError:
            end_frequency = None
            self.end_frequency.setText("")

        self.do_plot(
            receivers=receivers,
            target_date=target_date,
            start_frequency=start_frequency,
            end_frequency=end_frequency,
        )


def main():
    app = QtWidgets.QApplication(sys.argv)
    screen = Window()
    screen.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
