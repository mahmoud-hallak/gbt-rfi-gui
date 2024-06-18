import datetime
import os
import signal
import sys
import time



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

#Mahmoud imports
from scipy.signal import find_peaks
import plotly.graph_objects as go
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication
from PyQt5.QtWidgets import QDesktopWidget



#add .Ui file path here
qtCreatorFile = os.path.dirname(__file__) + "/RFI_GUI.ui"
Ui_MainWindow, QtBaseClass = loadUiType(qtCreatorFile)


#"self" cannot really be passed but still should be in the argument

#Need to pull some data qs and then


#get_scans gets the total number of scans

#do_plot plots plots the individual scans for this project 



#test project:
class Window(QMainWindow, Ui_MainWindow):

    def __init__(self):
        QtWidgets.QWidget.__init__(self)


        # Set up the UI file
    """
        self.setupUi(self)
        #mahmoud
        layout = QVBoxLayout()
        self.button = QPushButton('click to make highres plot', self)
        #self.graph_label = QLabel('Hightres plot', self)


        layout.addWidget(self.button)
        self.setLayout(layout)


        self.button.clicked.connect(self.toggle_graph(self))


    def toggle_graph(self):
        if self.button.isEnabled():
            high_resolution = True
            self.make_plot(,,,high_resolution)
            self.button.setEnabled()

    """

    def do_plot(self, session, high_resolution, receivers, start_date, end_date):
            # don't want to look at dates with no data, find the most recent session date
            

            start_time = time.time()



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



            #if you have an exact session inmind
            #qs = Frequency.objects.filter(scan__session__name=session)

            # make a 4 column dataFrame for the data needed to plot
            data = pd.DataFrame(
                qs.values("frequency", "intensity", "scan__datetime", "scan__session__name")
            )

            start_frequency = data["frequency"].min()

            end_frequency = data["frequency"].max()

            print("--- %s Data pulling: ---" % (time.time() - start_time))

            if not data.empty:
                # line plot
                self.make_plot(
                    data,
                    start_frequency,
                    end_frequency,
                    high_resolution,
                    start_time,
                )
                # color map graph, but only if there is more than one day with data
                unique_days = data.scan__datetime.unique()
                #self.make_color_plot(data, unique_days, receivers, end_date, start_date)

                # option to save the data from the plot
                #if self.saveData.isChecked():
                #    self.save_file(
                #       pd.DataFrame(qs.values("scan__datetime", "frequency", "intensity"))
                #    )


    def make_plot(
        self, data, start_frequency, end_frequency, high_resolution, start_time,
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
            #print(f"", proj_date[0], "\t\t", str(i))


        print("Original # of points displayed: " + str(len(full_data["intensity_mean"])))    

        #Mahmoud Edits

        start_time = time.time()


        if high_resolution == "orig":
            filtered_data = full_data
        elif high_resolution == "scipy":

            #Specify an threshold of useful points 
            intensity_threshold =  np.median(full_data['intensity_mean'])*100
            print("Threshold: " + str(intensity_threshold) + "Jy")

            #creates the simplified dataset (This keeps the graph from losing the zero markers)
            low_res_data =  full_data.iloc[::int(len(full_data["intensity_mean"])*0.005)] 
            print("lowres points displayed: " + str(len(low_res_data["intensity_mean"])))

            #Finds the points above the specified threshold, 
            peaks, _ = find_peaks(full_data['intensity_mean'], intensity_threshold)

            #takes out the peaks from the dataframe to be added later
            peaks_data = full_data.iloc[peaks] 

            #adds the high resolution peaks to the simplified dataset and sorts them
            filtered_data = pd.concat([peaks_data,low_res_data]).sort_values(by='frequency')

        elif high_resolution == "mean":
            intensity_threshold =  np.median(full_data['intensity_mean'])*100
            print("Threshold: " + str(intensity_threshold) + "Jy")

            #First smooth the data a bit simple mean smoothing for efficiency
            full_data = full_data.rolling(window=5).mean()

            #Remove the low intenisty points
            full_data = full_data[full_data['intensity_mean'] > intensity_threshold]

            #Select every other point
            filtered_data = full_data[::int(len(full_data["intensity_mean"])*0.00001)]
        
        print("--- %s filter time: seconds ---" % (time.time() - start_time))

        
        print("Total # of points displayed: " + str(len(filtered_data["intensity_mean"])))
        

        start_time = time.time()


        # Create the 2D line plot
        fig, ax = plt.subplots(1, figsize=(9, 4))
        plt.suptitle( high_resolution + ": Averaged RFI Environment at Green Bank Observatory" + "\n" + "# points: " + str(len(filtered_data["intensity_mean"])))
        plt.xlabel("Frequeny (MHz)")
        plt.ylabel("Average Intensity (Jy)")
        plt.ylim(-10, 500)
        plt.xlim(start_frequency, end_frequency)

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
        

        #Fills in the gaps and better highlight the peak groupings without the zigzag
        plt.fill_between(filtered_data["frequency"], filtered_data["intensity_mean"], color="black")




        #Dynamic plot

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

        #so it doesn't get stuck, we don't show the plot instead exit right away
        plt.show()
        plt.pause(0.0001)
        plt.close()
        print("--- %s plotting time: seconds ---" % (time.time() - start_time))


def main():

    #set variables for testing
    receivers = ['Rcvr2_3']
    end_date = datetime.datetime(2023, 1, 20, 0, 0, 0)
    start_date = datetime.datetime(2022, 1, 1, 0, 0, 0)
    start_frequency= None
    end_frequency= None
    

    end_date = end_date.replace(tzinfo=pytz.UTC)
    start_date = start_date.replace(tzinfo=pytz.UTC)


    signal.signal(signal.SIGINT, signal.SIG_DFL)
    


    user_input = str(input("Type of analysis ('orig, scipy, mean'): "))

    app = QtWidgets.QApplication(sys.argv)
    screen = Window()

    #screen.show()  for the widgets

    #string_array = ["TRFI_020423_S1","TRFI_020623_S1","TRFI_020623_S2","TRFI_020723_S1","TRFI_020823_S1"]


    Window.do_plot(Window(),
            session = "TRFI_110823_S1",
            high_resolution = user_input,
            receivers = receivers,
            start_date = start_date,
            end_date = end_date,
        )


    

    #sys.exit(app.exec_())
    

if __name__ == "__main__":
    main()



