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
import plotly.graph_objects as go
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication
from PyQt5.QtWidgets import QDesktopWidget

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

    def do_plot(self, receivers, start_date, end_date, start_frequency, end_frequency, high_resolution):
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
                high_resolution,
            )
            # color map graph, but only if there is more than one day with data
            unique_days = data.scan__datetime.unique()
            self.make_color_plot(data, unique_days, receivers, end_date, start_date)

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
        self, receivers, data, end_date, start_date, start_frequency, end_frequency, high_resolution
    ):
        # make a new object with the average intensity for the 2D plot
        mean_data_intens = data.groupby(
            ["scan__datetime", "frequency", "scan__session__name"]
        ).agg({"intensity": ["mean"]})
        mean_data_intens.columns = ["intensity_mean"]
        mean_data = mean_data_intens.reset_index()
        # sort values so the plot looks better, this has nothing to do with the actual data
        full_data = mean_data.sort_values(by=["frequency", "intensity_mean"])

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
        sort_by_date = full_data.sort_values(by=["scan__session__name"])
        project_ids = sort_by_date["scan__session__name"].unique()
        for i in project_ids:
            proj_date = sort_by_date[
                sort_by_date["scan__session__name"] == i
            ].scan__datetime.unique()
            proj_date = proj_date.strftime("%Y-%m-%d")
            print(f"", proj_date[0], "\t\t", str(i))


        if high_resolution:
            filtered_data = full_data
        else:

            #Specify an threshold of useful points 
            intensity_threshold =  np.median(full_data['intensity_mean'])*100
            print("Threshold: " + str(intensity_threshold) + "Jy")

            #creates the simplified dataset (This keeps the graph from losing the zero markers)
            low_res_data =  full_data.iloc[::int(len(full_data["intensity_mean"])*0.001)] 
            print("lowres points displayed: " + str(len(low_res_data["intensity_mean"])))


            #for the really big data sets, filter by peak distance
            if(len(full_data["intensity_mean"]) > 400000):
                print("advanced filtering")
                peaks, _ = find_peaks(full_data['intensity_mean'], intensity_threshold, distance=5)
            else:
                peaks, _ = find_peaks(full_data['intensity_mean'], intensity_threshold)

            #takes out the peaks from the dataframe to be added later
            peaks_data = full_data.iloc[peaks] 

            #adds the high resolution peaks to the simplified dataset and sorts them
            filtered_data = pd.concat([peaks_data,low_res_data]).sort_values(by='frequency')

        print("Original # of points displayed: " + str(len(full_data["intensity_mean"])))

        print(" - Filtered # of points displayed: " + str(len(filtered_data["intensity_mean"])))

        # Create the 2D line plot
        fig, ax = plt.subplots(1, figsize=(9, 4))
        plt.title(txt, fontsize=8)
        plt.suptitle("Averaged RFI Environment at Green Bank Observatory")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Average Intensity (Jy)")
        plt.ylim(-10, 500)
        plt.xlim(start_frequency, end_frequency)

        plt.fill_between(filtered_data["frequency"], filtered_data["intensity_mean"], color="black")


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
            filtered_data["frequency"],
            filtered_data["intensity_mean"],
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


        def on_lims_change(event_ax):


            #window width
            windowsize = self.size().width()


            #Finds the x and y limits of this new interval
            freq_min = event_ax.get_xlim()[0]
            freq_max = event_ax.get_xlim()[1]

            inten_min = event_ax.get_ylim()[0]
            inten_max = event_ax.get_ylim()[1]

            #calculates the amount of displayed points on the screen
            pts_per_freq = len(filtered_data["frequency"])/(end_frequency-start_frequency) 
            pts_per_pixel = len(filtered_data["frequency"])/windowsize
            displayed_pts = pts_per_freq*(freq_max-freq_min)


            #clears the plt to regraph
            plt.cla()


            #Is true if there isn't enough points for pixels on the screen
            if( 1.5 >= (displayed_pts/windowsize)):
                
                print("regraphing") 

                #makes a cropped df of full data
                interval_data = full_data[(full_data['frequency'] >= freq_min) & (full_data['frequency'] <= freq_max)]



            else:
                #pulls back the scipy filtered data
                interval_data = filtered_data
                plt.fill_between(filtered_data["frequency"], filtered_data["intensity_mean"], color="black")


            #replots
            plt.plot(
                interval_data["frequency"],
                interval_data["intensity_mean"],
                color="black",
                linewidth=0.5,
            )
            plt.xlim(freq_min,freq_max)  # Set xlim explicitly
            plt.ylim(inten_min, inten_max)
            ax.figure.canvas.draw_idle()


            # The only way to get it to update again was putting those commands in this def
            ax.callbacks.connect('xlim_changed', on_lims_change)
            ax.callbacks.connect('ylim_changed', on_lims_change)

                
        #checks if the axis change
        ax.callbacks.connect('xlim_changed', on_lims_change)
        ax.callbacks.connect('ylim_changed', on_lims_change)

        # Plot one or both the line plot and the annotations
        
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
        print(type(start_date))
        print(start_date)
        print(receivers)
        self.do_plot(
            receivers=receivers,
            end_date=end_date,
            start_date=start_date,
            start_frequency=start_frequency,
            end_frequency=end_frequency,
            high_resolution=False,
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
