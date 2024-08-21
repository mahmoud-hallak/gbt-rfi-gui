import datetime
import os
import signal
import sys


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rfi_query.settings")

import django

django.setup()


import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytz
from matplotlib.artist import Artist
from PyQt5 import QtGui, QtWidgets
from PyQt5.Qt import QMainWindow
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.uic import loadUiType

from rfi.models import Frequency, Scan


from scipy.signal import find_peaks
#import plotly.graph_objects as go
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication, QCheckBox
#from PyQt5.QtWidgets import QDesktopWidget

import time
#from django.db.models import Q


# add .Ui file path here
qtCreatorFile = os.path.dirname(__file__) + "/RFI_GUI.ui"
Ui_MainWindow, QtBaseClass = loadUiType(qtCreatorFile)


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        # Set up the UI file
        self.setupUi(self)

        # to protect the database, restrict time ranges
        self.MAX_TIME_RANGE = datetime.timedelta(days=365)

        # List of receivers
        self.receivers.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        # recievers need to be in a sorted list
        rcvrs = [
            "Prime Focus 1",
            "L-band",
            "S-band",
            "C-band",
            "X-band",
            "Ku-band",
            "K-band FPA",
            "Ka-band",
            "Q-band",
        ]
        self.receivers.addItems(rcvrs)

        # Start and Stop Date DateEdit widgets
        self.end_date.setDate(datetime.datetime.today())
        self.start_date.setDate(datetime.datetime.today() - datetime.timedelta(days=7))
        self.setEndDate()
        self.start_date.dateChanged.connect(self.setEndDate)

        # Frequency Range
        self.start_frequency.setValidator(QtGui.QDoubleValidator())
        self.end_frequency.setValidator(QtGui.QDoubleValidator())

        # Push Button to get data
        self.plot_button.clicked.connect(self.clicked)

        # connect menus
        self.actionQuit.triggered.connect(self.menuQuit)
        self.actionAbout.triggered.connect(self.menuAbout)



        self.toggle_resolution = QCheckBox("Toggle High Resolution to save the full data", self)

        self.setMenuWidget(self.toggle_resolution)




    def get_scans(self, receivers, target_date, start_frequency, end_frequency):
        # don't want to look at dates with no data, find the most recent session date
        most_recent_session_prior_to_target_datetime = (
            Scan.objects.filter(datetime__lte=end_date)
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
            qs = qs.filter(frontend__name__in=receivers)

        if end_date:
            qs = qs.filter(datetime__lte=end_date)
        if start_date:
            qs = qs.filter(datetime__lte=start_date)

        if start_frequency:
            qs = qs.filter(frequency__frequency__gte=start_frequency)

        if end_frequency:
            qs = qs.filter(frequency__frequency__lte=end_frequency)

        return qs

    def do_plot(
        self,
        receivers,
        start_date,
        end_date,
        start_frequency,
        end_frequency,
    ):
        # don't want to look at dates with no data, find the most recent session date
        most_recent_session_prior_to_target_datetime = (
            Scan.objects.filter(datetime__lte=end_date, frontend__name__in=receivers)
            .order_by("-datetime")
            .first()
            .datetime
        )

        qs = Frequency.objects.all()

        if receivers:
            qs = qs.filter(scan__frontend__name__in=receivers)

        if end_date:
            if start_date > most_recent_session_prior_to_target_datetime:
                difference = end_date - start_date
                end_date = most_recent_session_prior_to_target_datetime
                start_date = end_date - difference
                QtWidgets.QMessageBox.information(
                    self,
                    "No Data Found",
                    f"""Your target date range holds no data \n  Displaying a new range with the most recent session data \n New range is {start_date.date()} to {end_date.date()}""",
                    QtWidgets.QMessageBox.Ok,
                )

            qs = qs.filter(scan__datetime__lte=end_date)
            qs = qs.filter(scan__datetime__gte=start_date)

        if start_frequency:
            qs = qs.filter(frequency__gte=start_frequency)

        if end_frequency:
            qs = qs.filter(frequency__lte=end_frequency)



        #if the high resolution button is not checked
        if not self.toggle_resolution.isChecked():
            qs = qs.filter(view_level_0=True)


        # make a 4 column dataFrame for the data needed to plot
        data = pd.DataFrame(
            qs.values("frequency", "intensity", "scan__datetime", "scan__session__name")
        )


        if not start_frequency:
            start_frequency = data["frequency"].min()
        if not end_frequency:
            end_frequency = data["frequency"].max()
        if not data.empty:
            # line plot
            self.make_plot(
                receivers,
                data,
                end_date,
                start_date,
                start_frequency,
                end_frequency,
            )
            # color map graph, but only if there is more than one day with data
            unique_days = data.scan__datetime.unique()
            #self.make_color_plot(data, unique_days, receivers, end_date, start_date)

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



    
    def dynamic_query(self, freq_min, freq_max, sessions, zoom):

        qs = Frequency.objects.all()

        #find the sessions
        qs = qs.filter(scan__session__name__in=sessions)

        #filter data by the zoom and freq_min and freq_max
        qs = qs.filter(frequency__gte=freq_min, frequency__lte=freq_max)
        
        if(zoom == 0):
            qs = qs.filter(view_level_0=True)
        elif (zoom == 1):
            qs = qs.filter(view_level_1=True)
        elif(zoom == 2):
            qs = qs.filter(view_level_2=True)
        elif(zoom == 3):
            qs = qs.filter(view_level_3=True)
        #check if the interval allows for

        #add them together and average the mean


        data = pd.DataFrame(
                qs.values("frequency", "intensity", "scan__datetime", "scan__session__name")
                )

        mean_data_intens = data.groupby(
            ["scan__datetime", "frequency", "scan__session__name"]
        ).agg({"intensity": ["mean"]})
        mean_data_intens.columns = ["intensity_mean"]
        mean_data = mean_data_intens.reset_index()
        # sort values so the plot looks better, this has nothing to do with the actual data
        df = mean_data.sort_values(by=["frequency", "intensity_mean"])

        return df



    def make_plot(
        self,
        receivers,
        data,
        end_date,
        start_date,
        start_frequency,
        end_frequency,
    ):

        high_resolution = self.toggle_resolution.isChecked()

        # make a new object with the average intensity for the 2D plot
        mean_data_intens = data.groupby(
            ["scan__datetime", "frequency", "scan__session__name"]
        ).agg({"intensity": ["mean"]})
        mean_data_intens.columns = ["intensity_mean"]
        mean_data = mean_data_intens.reset_index()
        # sort values so the plot looks better, this has nothing to do with the actual data
        mean_data = mean_data.sort_values(by=["frequency", "intensity_mean"])

        # generate the description fro the plot
        txt = f" \
            Your data summary for this plot: \n \
            Receiver : {receivers} \n \
            Date range : From {start_date.date()} to {end_date.date()} \n \
            Frequency Range : {mean_data['frequency'].min()}MHz to {mean_data['frequency'].max()}MHz "

        # print out info for investagative GBO scientists
        print("Your requested projects are below:")
        print("Session Date \t\t Project_ID")
        print("-------------------------------------")
        sort_by_date = mean_data.sort_values(by=["scan__session__name"])
        project_ids = sort_by_date["scan__session__name"].unique()
        for i in project_ids:
            proj_date = sort_by_date[
                sort_by_date["scan__session__name"] == i
            ].scan__datetime.unique()
            proj_date = proj_date.strftime("%Y-%m-%d")
            print(f"", proj_date[0], "\t\t", str(i))

        # if the resolution was selected or if the data isn't big enough
        if high_resolution:

            dynamic = False

        else:
            dynamic = True

        print("data points: " + str(len(mean_data["frequency"])))

        # Create the 2D line plot
        fig, ax = plt.subplots(1, figsize=(9, 4))
        plt.title(txt, fontsize=8)
        plt.suptitle("Averaged RFI Environment at Green Bank Observatory")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Average Intensity (Jy)")
        plt.ylim(-10, 500)
        plt.xlim(start_frequency, end_frequency)

        # Create the annotations for RFI, only plot if user selects
        if self.yes_annotate.isChecked():
            self.getrfi = self.getrfi_func(start_frequency, end_frequency)

            def onclick(event):
                click_rfi = self.getrfi.copy()
                click_rfi.drop(
                    click_rfi[click_rfi["start"] > event.xdata].index, inplace=True
                )
                click_rfi.drop(
                    click_rfi[click_rfi["end"] < event.xdata].index, inplace=True
                )
                click_rfi = click_rfi.reset_index()

                # if you click outside the plot you return all values - we want to return none
                if len(click_rfi) == len(self.getrfi.copy()):
                    click_rfi = pd.DataFrame(columns=click_rfi.columns)

                for row in range(click_rfi.shape[0]):
                    print(
                        f"{click_rfi['comments'][row]} : {click_rfi['start'][row]} - {click_rfi['end'][row]} MHz"
                    )
                    mid = (click_rfi["end"][row] - click_rfi["start"][row]) / 2
                    annot = ax.annotate(
                        text=click_rfi["comments"][row],
                        xy=(click_rfi["start"][row] + mid, 0),
                        xytext=(click_rfi["start"][row] + mid, 300),
                        ha="center",
                        textcoords="data",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->", color="green"),
                        wrap=True,
                    )
                    fig.canvas.draw()
                    Artist.remove(annot)

            if len(self.getrfi) > 0:
                for row in range(self.getrfi.shape[0]):
                    krfi = ax.axvspan(
                        self.getrfi["start"][row],
                        self.getrfi["end"][row],
                        color="purple",
                        alpha=0.4,
                    )

                fig.canvas.mpl_connect("button_press_event", onclick)

        plt.plot(
            mean_data["frequency"],
            mean_data["intensity_mean"],
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

        """
        Dynamic plotting command, activated by matplot axis changing
        """

        #sets the variables needed for the dynamic 
        sessions = mean_data['scan__session__name'].sort_values().unique()
        self.zoom = 0
        self.interval_data = mean_data

        large_sessions = np.array(["Prime Focus 1", "Rcvr1_2", "Rcvr4_6", "RcvrArray18_26", "Rcvr26_40", "Rcvr40_52"])

        is_large_session = receivers in large_sessions 

        more_than_10 = len(sessions) > 10


        def on_lims_change(event_ax):

            windowsize = self.size().width()

            # Finds the x and y limits of this new interval
            freq_min, freq_max = event_ax.get_xlim()
            inten_min, inten_max = event_ax.get_ylim()

            #Finds the max/min frequency of the interval
            df_freq_max = mean_data["frequency"].max()
            df_freq_min = mean_data["frequency"].min()

            pts_per_freq = len(mean_data["frequency"]) / (
                df_freq_max - df_freq_min
            )

            freq_diff = freq_max-freq_min

            displayed_pts = pts_per_freq * (freq_max - freq_min)

            #start by not replotting, and change if needed
            replot = False


            #checks if its panning motion or zooming (rounds to whole number)
            if (round(freq_diff*2,0) != 
                round((self.interval_data["frequency"].max() - self.interval_data["frequency"].min()),0)):

                replot = True

                if 1 > (displayed_pts / windowsize):
                    self.zoom =  1

                if 0.4 > (displayed_pts / windowsize):
                    self.zoom = 2

                if 0.07 > (displayed_pts / windowsize):
                    self.zoom = 3

                if not (is_large_session or more_than_10):
                    self.zoom = 4

                if 0.02 > (displayed_pts / windowsize):
                    self.zoom = 4

                if 2 < (displayed_pts / windowsize):
                    # pulls back the scipy filtered data
                    self.interval_data = mean_data
                    self.zoom =  0

                # incase the user zooms back out, it will assign the already pulled data instead of querying (Faster)
                if(self.zoom == 0):
                    self.interval_data = mean_data
                else:
                    self.interval_data = self.dynamic_query(freq_min-freq_diff*0.5, freq_max+freq_diff*0.5, sessions, self.zoom)

            #this checks if we go out of bounds, and calls to replot more points (Causes a minor graph lag when paning)
            elif(self.zoom and (self.interval_data["frequency"].max() < freq_max or self.interval_data["frequency"].min() > freq_min)):
                self.interval_data = self.dynamic_query(freq_min-freq_diff*0.5, freq_max+freq_diff*0.5, sessions, self.zoom)
                replot = True
            
            # replots
            if(replot):
                print("replotting")
                plt.cla()
                plt.plot(
                    self.interval_data["frequency"],
                    self.interval_data["intensity_mean"],
                    color="black",
                    linewidth=0.5,
                )
                plt.xlim(freq_min, freq_max)  # Set xlim explicitly
                plt.ylim(inten_min, inten_max)
                ax.figure.canvas.draw_idle()
                ax.callbacks.connect("xlim_changed", on_lims_change)

        # no dynamic updating unless checked
        if dynamic:
            ax.callbacks.connect("xlim_changed", on_lims_change)

        plt.show()

    def make_color_plot(self, data, unique_days, receivers, end_date, start_date):
        # set up the subplots
        number_of_subplots = len(unique_days)
        fig, axes = plt.subplots(number_of_subplots, 1, figsize=(10.5, 7), sharex=True)
        # account for the single day plots
        if number_of_subplots == 1:
            axes = [axes]

        # generate the description fro the plot
        txt = f" \
            Your data summary for this plot: \n \
            Receiver : {receivers} \n \
            Date range : From {start_date.date()} to {end_date.date()} \n \
            Frequency Range : {data['frequency'].min()}MHz to {data['frequency'].max()}MHz "

        session = 0
        for ax in axes:
            # make a new range of dates based on the session of interest
            date_of_interest = data.scan__datetime  # get the dates
            date_of_interest_sorted = (
                date_of_interest.sort_values()
            )  # sort for the plot
            date_of_interest_datetime = date_of_interest_sorted.unique()[
                session
            ].to_pydatetime()

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
                cmap="viridis",
            )

            # only want the session for the ylabel
            ax.set_yticklabels([])
            ax.set_ylabel(str(date_of_interest_datetime.date()), rotation="horizontal")
            ax.yaxis.set_label_coords(-0.08, 0.5)

            if session == 0:
                ax.set_title(txt, fontsize=8)

            # increase the session index
            session = session + 1

        # set the xlim to cover the whole range of frequency for all sessions
        plt.xlim(data.frequency.min(), data.frequency.max())

        # move the color bar to account for all subplots
        fig.subplots_adjust(right=0.8)
        cbar = fig.colorbar(im, cax=fig.add_axes([0.85, 0.15, 0.05, 0.7]))

        # set labels
        fig.text(0.5, 0.04, "Frequency (MHz)", ha="center")
        fig.text(0.01, 0.5, "Session Dates (UTC)", va="center", rotation="vertical")
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
            "This GUI provides reduced RFI scans. \n\n The plots provided "
            "give the user a look at the frequency vs averaged intensity "
            "of RFI scans averaged over a given time range. \n\n A color plot "
            "of all sessions in a given time frame is provided for ranges "
            "with more than one session. \n\n The full receiver bandwidth can "
            "be viewed by selecting a receiver or a more specified bandwidth "
            "can be selected by inputting a start and stop frequency. \n\n For "
            "Prime Focus receivers, users should provide the frequency "
            "range of the receiver.",
        )

    def menuQuit(self):
        """Method to handle the quit menu."""
        print("Thanks for using the gbt_rfi_gui!")
        sys.exit()

    def setEndDate(self):
        # don't let the user pick anything over 1 year away from the start_date
        max_date = self.start_date.dateTime().toPyDateTime().replace(tzinfo=pytz.UTC)
        self.end_date.setMaximumDate(max_date + self.MAX_TIME_RANGE)
        self.end_date.setMinimumDate(max_date)

    def clicked(self):
        # change the color so the user knows that it is plotting
        self.plot_button.setStyleSheet("background-color : green")
        self.plot_button.setText("Currently Plotting")
        self.plot_button.setEnabled(False)
        self.plot_button.repaint()

        rcvrs_dict = {
            "Prime Focus 1": "Prime Focus 1",
            "L-band": "Rcvr1_2",
            "S-band": "Rcvr2_3",
            "C-band": "Rcvr4_6",
            "X-band": "Rcvr8_10",
            "Ku-band": "Rcvr12_18",
            "K-band FPA": "RcvrArray18_26",
            "Ka-band": "Rcvr26_40",
            "Q-band": "Rcvr40_52",
        }

        receivers_band = [i.text() for i in self.receivers.selectedItems()]
        receivers = []
        for rcvr in receivers_band:
            receivers.append(rcvrs_dict[rcvr])

        # account for the user not selecting a rcvr
        if len(receivers) == 0:
            receivers = ["Prime Focus 1"]

        end_date = self.end_date.dateTime().toPyDateTime().replace(tzinfo=pytz.UTC)
        start_date = self.start_date.dateTime().toPyDateTime().replace(tzinfo=pytz.UTC)

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
            end_date=end_date,
            start_date=start_date,
            start_frequency=start_frequency,
            end_frequency=end_frequency,
        )

        # change the color so the user knows that it is done plotting
        self.plot_button.setStyleSheet("background-color : rgb(229, 229, 229)")
        self.plot_button.setText("Plot for these Args")
        self.plot_button.setEnabled(True)

    # get known rfi data
    def getrfi_func(self, start_frequency, end_frequency):
        getrfi = pd.read_csv(
            os.path.dirname(__file__) + r"/fccsheet.csv",
            usecols=["start", "end", "comments"],
        )

        getrfi.drop(getrfi[getrfi["start"] < start_frequency].index[:-1], inplace=True)
        getrfi.drop(getrfi[getrfi["end"] > end_frequency].index[1:], inplace=True)
        # reset
        getrfi = getrfi.reset_index()
        return getrfi


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QtWidgets.QApplication(sys.argv)
    screen = Window()
    screen.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
