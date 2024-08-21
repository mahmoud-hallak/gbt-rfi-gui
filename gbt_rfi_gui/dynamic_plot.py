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

    stuff= Frequency()._meta

    fields = stuff.get_fields()

    # Extract and print the names of the fields
    field_names = [field.name for field in fields]
    print(field_names)


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

    def do_plot(self, session, zoomed, receivers, start_date, end_date):
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


            fig, ax = plt.subplots(1, figsize=(9, 4))

            if not data.empty:
                # line plot
                self.make_plot(
                    data,
                    start_frequency,
                    end_frequency,
                    zoomed,
                    start_time,
                    fig, 
                    ax,
                )
                # color map graph, but only if there is more than one day with data
                unique_days = data.scan__datetime.unique()
                self.make_color_plot(data, unique_days, receivers, end_date, start_date)

                # option to save the data from the plot
                #if self.saveData.isChecked():
                #    self.save_file(
                #       pd.DataFrame(qs.values("scan__datetime", "frequency", "intensity"))
                #    )


    def make_plot(
        self, data, start_frequency, end_frequency, zoomed, start_time, fig, ax,
    ):
        # make a new object with the average intensity for the 2D plot
        
        if not zoomed:
            mean_data_intens = data.groupby(
                ["scan__datetime", "frequency", "scan__session__name"]
            ).agg({"intensity": ["mean"]})
            mean_data_intens.columns = ["intensity_mean"]
            mean_data = mean_data_intens.reset_index()
            # sort values so the plot looks better, this has nothing to do with the actual data
            sorted_mean_data = mean_data.sort_values(by=["frequency", "intensity_mean"])

            # generate the description fro the plot
            # print out info for investagative GBO scientists
            print("-------------------------------------")
            sort_by_date = sorted_mean_data.sort_values(by=["scan__session__name"])
            project_ids = sort_by_date["scan__session__name"].unique()
            for i in project_ids:
                proj_date = sort_by_date[
                    sort_by_date["scan__session__name"] == i
                ].scan__datetime.unique()
                proj_date = proj_date.strftime("%Y-%m-%d")
                #print(f"", proj_date[0], "\t\t", str(i))



#plots only the points in the place we zoomed in
        elif zoomed:
            sorted_data = sorted_mean_data[(
                sorted_mean_data['frequency'] >= start_frequency) 
                & (sorted_mean_data['frequency'] <= end_frequency)]


    
       
        if zoomed:
            #Specify an threshold of useful points 
            intensity_threshold =  np.median(sorted_mean_data['intensity_mean'])*100
            print("Threshold: " + str(intensity_threshold) + "Jy")

            #creates the simplified dataset (This keeps the graph from losing the zero markers)
            low_res_data =  sorted_mean_data.iloc[::int(len(sorted_mean_data["intensity_mean"])*0.005)] 
            print("lowres points displayed: " + str(len(low_res_data["intensity_mean"])))

            #Finds the points above the specified threshold, 
            peaks, _ = find_peaks(sorted_mean_data['intensity_mean'], intensity_threshold)

            #takes out the peaks from the dataframe to be added later
            peaks_data = sorted_mean_data.iloc[peaks] 

            #adds the high resolution peaks to the simplified dataset and sorts them
            sorted_data = pd.concat([peaks_data,low_res_data]).sort_values(by='frequency')

        print("--- %s filter time: seconds ---" % (time.time() - start_time))

        
        #print("Total # of points displayed: " + str(len(sorted_data["intensity_mean"])))
        

        start_time = time.time()


        print("Start: " + str(start_frequency))


        # Create the 2D line plot
        #The if statment is to make sure that we don't make a new graph
        if not zoomed:
            plt.ylim(-10, 500)
        
        plt.suptitle("Averaged RFI Environment at Green Bank Observatory" + "\n" + "# points: " + str(len(sorted_data["intensity_mean"])))
        plt.xlabel("Frequeny (MHz)")
        plt.ylabel("Average Intensity (Jy)")
        plt.xlim(start_frequency, end_frequency)

        plt.plot(
            sorted_data["frequency"],
            sorted_data["intensity_mean"],
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
        

        #6/10 addition, to fill in the gaps and better highlight the peak groupings without the zigzag
        plt.fill_between(sorted_data["frequency"], sorted_data["intensity_mean"], color="black")


        #Dynamic plot edits


        def on_lims_change(event_ax):
            #print (event_ax.get_xlim())

            #window width 
            windowsize = 640

            freq_min = event_ax.get_xlim()[0]
            freq_max = event_ax.get_xlim()[1]


            #if the zoom size is less than 10% of the ori
            if( 0.10 >= (event_ax.get_xlim()[1]-event_ax.get_xlim()[0])/windowsize):
                
                print("regraphing") 

                plt.cla()

                #interval_data = sorted_mean_data[(sorted_mean_data['frequency'] >= freq_min) & (sorted_mean_data['frequency'] <= freq_max)]

                self.make_plot(data, freq_min, freq_max, True, start_time,fig,ax)
        
        ax.callbacks.connect('xlim_changed', on_lims_change)
        ax.callbacks.connect('ylim_changed', on_lims_change)


        #so it doesn't get stuck, we don't show the plot instead exit right away
        plt.show()
        plt.pause(0.0001)
        plt.close()
        
        
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
    

    app = QtWidgets.QApplication(sys.argv)
    screen = Window()

    #screen.show()  for the widgets

    #string_array = ["TRFI_020423_S1","TRFI_020623_S1","TRFI_020623_S2","TRFI_020723_S1","TRFI_020823_S1"]

    Window.do_plot(Window(),
            session = "TRFI_110823_S1",
            zoomed = False,
            receivers = receivers,
            start_date = start_date,
            end_date = end_date,
        )


    

    #sys.exit(app.exec_())
    

if __name__ == "__main__":
    main()