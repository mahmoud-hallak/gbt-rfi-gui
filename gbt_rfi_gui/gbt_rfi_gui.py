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

from rfi.models import Frequency, Scan

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
        # self.setGeometry(0, 0, 449, 456)

        # to protect the database, restrict time ranges
        self.Day_RANGE = datetime.timedelta(days=1)
        self.Mth_RANGE = datetime.timedelta(days=30)
        self.Yr_RANGE = datetime.timedelta(days=365)

        # List of receivers
        self.receivers.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        # recievers need to be in a sorted list
        rcvrs = [
            "Prime Focus 1",
            "Rcvr_800",
            "Prime Focus 2",
            "Rcvr1_2",
            "Rcvr2_3",
            "Rcvr4_6",
            "Rcvr8_10",
            "Rcvr12_18",
            "RcvrArray18_26",
            "Rcvr26_40",
            "Rcvr40_52",
        ]
        self.receivers.addItems(rcvrs)

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
        #    dont want to poll all scans
        qs = Scan.objects.filter(
            scan__session=most_recent_session_prior_to_target_datetime
        )

        if receivers:
            print(f"Filtering by {receivers=}")
            qs = qs.filter(frontend__name__in=receivers)

        if target_date:
            end_date = self.get_end_date(target_date)
            if end_date > most_recent_session_prior_to_target_datetime:
                target_date = most_recent_session_prior_to_target_datetime
                end_date = self.get_end_date(target_date)
            print(f"Filtering by {target_date=}")
            print(f"Starting from {target_date.date()} to {end_date.date()}")
            qs = qs.filter(datetime__lte=target_date)
            qs = qs.filter(datetime__gte=end_date)

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
            Scan.objects.filter(datetime__lte=target_date, frontend__name__in=receivers)
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
            target_date, end_date = self.get_end_date(target_date)
            if end_date > most_recent_session_prior_to_target_datetime:
                QtWidgets.QMessageBox.information(
                    self,
                    "No Data Found",
                    "Your target date range holds no data \n Displaying a new range with the most recent session data",
                    QtWidgets.QMessageBox.Ok,
                )
                target_date = most_recent_session_prior_to_target_datetime
                target_date, end_date = self.get_end_date(target_date)
                print(
                    "Your target date range holds no data -- Displaying a new range with the most recent session data"
                )
            print(f"Filtering by {target_date=}")
            print(f"Starting from {target_date.date()} to {end_date.date()}")
            qs = qs.filter(scan__datetime__lte=target_date)
            qs = qs.filter(scan__datetime__gte=end_date)

        if start_frequency:
            print(f"Filtering by {start_frequency=}")
            qs = qs.filter(frequency__gte=start_frequency)

        if end_frequency:
            print(f"Filtering by {end_frequency=}")
            qs = qs.filter(frequency__lte=end_frequency)

        # make a 3 column dataFrame for the data needed to plot
        data = pd.DataFrame(qs.values("frequency", "intensity", "scan__datetime"))

        if not data.empty:
            self.make_plot(
                receivers,
                data,
                target_date,
                end_date,
                start_frequency,
                end_frequency,
            )
            # Plot the color map graph, but only if there is more than one day with data
            unique_days = data.scan__datetime.unique()
            if len(unique_days) > 1:
                self.make_color_plot(data, unique_days)

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

    def make_plot(
        self, receivers, data, target_date, end_date, start_frequency, end_frequency
    ):
        # make a new object with the average intensity for the 2D plot
        mean_data_intens = data.groupby(["scan__datetime", "frequency"]).agg(
            {"intensity": ["mean"]}
        )
        mean_data_intens.columns = ["intensity_mean"]
        mean_data = mean_data_intens.reset_index()
        # sort values so the plot looks better, this has nothing to do with the actual data
        sorted_mean_data = mean_data.sort_values(by=["frequency", "intensity_mean"])

        # generate the description fro the plot
        txt = f" \
            Your data summary for this plot: \n \
            Receiver : {receivers[0]} \n \
            Date range : From {end_date.date()} to {target_date.date()} \n \
            Frequency Range : {mean_data['frequency'].min()}MHz to {mean_data['frequency'].max()}MHz "

        # Plot the 2D graph
        plt.figure(figsize=(9, 4))
        plt.title(txt, fontsize=8)
        plt.suptitle("Averaged RFI Environment at Green Bank Observatory")
        plt.xlabel("Frequency MHz")
        plt.ylabel("Average Intensity Jy")
        plt.plot(
            sorted_mean_data["frequency"],
            sorted_mean_data["intensity_mean"],
            color="black",
            linewidth=0.5,
        )
        # make sure the titles align correctly
        plt.tight_layout()
        # setting the location of the window
        mngr = plt.get_current_fig_manager()
        geom = mngr.window.geometry()
        x, y, dx, dy = geom.getRect()
        # display the plot to the right of the ui
        mngr.window.setGeometry(459, 0, dx, dy)
        plt.show()

    def make_color_plot(self, data, unique_days):
        # set up the subplots
        number_of_subplots = len(unique_days)
        fig, axes = plt.subplots(number_of_subplots, 1, figsize=(10.5, 7), sharex=True)

        session = 0
        for ax in axes:
            # make a new range of dates based on the session of interest
            date_of_interest = data.scan__datetime  # get the dates
            date_of_interest_sorted = (
                date_of_interest.sort_values()
            )  # sort for the plot
            date_of_interest_datetime = date_of_interest_sorted.unique()[
                session
            ].to_pydatetime()  # get one day and convert to pyDatetime

            unique_date_range = data[
                data["scan__datetime"] == date_of_interest_datetime
            ]  # get the data but only for one session of interest at a time

            # make the date bins for plotting
            widen = datetime.timedelta(hours=1)
            date_bins = np.arange(
                date_of_interest_datetime - widen,
                date_of_interest_datetime + widen,
                datetime.timedelta(hours=1),
            ).astype(datetime.datetime)
            # Get the center of the date bins (for plotting)
            dates = date_bins[:-1] + 0.5 * np.diff(date_bins)
            # Convert from datetime so imshow recignizes the extent format
            date_extents = mdates.date2num(dates)

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

            im = ax.imshow(
                np.log10(timeseries_rfi.unstack()),
                origin="lower",
                aspect="auto",
                # there is only one date of interest per subplot so date extents are to artifically expanded
                extent=(freqs[0], freqs[-1], date_extents[0] - 1, date_extents[-1] + 1),
                interpolation="none",
            )

            # only want the session for the ylabel
            ax.set_yticklabels([])
            ax.set_ylabel(str(date_of_interest_datetime.date()), rotation="horizontal")
            ax.yaxis.set_label_coords(-0.08, 0.5)

            # increase the session index
            session = session + 1

        # set the xlim to cover the whole range of frequency for all sessions
        plt.xlim(data.frequency.min(), data.frequency.max())

        # move the color bar to account for all subplots
        fig.subplots_adjust(right=0.8)
        cbar = fig.colorbar(im, cax=fig.add_axes([0.85, 0.15, 0.05, 0.7]))

        # set labels
        fig.text(0.5, 0.04, "Frequency (MHz)", ha="center")
        fig.text(0.01, 0.5, "Session Dates", va="center", rotation="vertical")
        cbar.set_label("log(flux) [Jy]")
        plt.suptitle("RFI Environment at Green Bank Observatory per Session")

        # settign the location of the window
        mngr = plt.get_current_fig_manager()
        geom = mngr.window.geometry()
        x, y, dx, dy = geom.getRect()
        # display the plot under the ui
        mngr.window.setGeometry(0, 456, dx, dy)

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
            "Automated RFI Scan Data Reduction GUI",
            """This GUI provides reduced RFI scans. \n\n The plots provided
             give the user a look at the frequency vs averaged intensity
             of RFI scans averaged over a given time range. \n A color plot
             of all sessions in a given time frame is provided for ranges
             with more than one session. \n The full receiver bandwidth can
             be viewed by selecting a receiver or a more specified bandwidth
             can be selected by inputting a start and stop frequency. \n For
             Prime Focus receivers, users should provide the frequency
             range of the receiver.""",
        )

    def menuQuit(self):
        """Method to handle the quit menu."""
        print("Thanks for using the gbt_rfi_gui")
        sys.exit()

    def get_end_date(self, target_date):
        # default is 1Day -- M for Month/30Days, Y for Year/365Days
        if self.radioButtonD.isChecked():
            end_date = target_date
            target_date = target_date + self.Day_RANGE
        if self.radioButtonM.isChecked():
            end_date = target_date - self.Mth_RANGE
        if self.radioButtonY.isChecked():
            end_date = target_date - self.Yr_RANGE
        return target_date, end_date

    def clicked(self):
        receivers = [i.text() for i in self.receivers.selectedItems()]
        # account for the user not selecting a rcvr
        if len(receivers) == 0:
            receivers = ["Prime Focus 1"]

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
