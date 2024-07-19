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
import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots
from PyQt5.QtWebEngineWidgets import QWebEngineView



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


    def plotly(self,plot_html):

        self.setWindowTitle("graph")

        self.plot_widget = QWebEngineView()

        self.plot_widget.setHtml(plot_html)

        self.setCentralWidget(self.plot_widget)

        self.show()




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


            qs = qs.filter(is_peak=True)

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


        frequency = filtered_data["frequency"]
        intensity_mean = filtered_data["intensity_mean"]


        # Create the 2D line plot
        fig = make_subplots(rows=1, cols=1)

        # Initial plot
        fig.add_trace(
            go.Scatter(
                x=frequency,
                y=intensity_mean,
                mode='lines',
                line=dict(color='black', width=0.5),
                fill='tozeroy',  # Fills area below the line to zero y
            )
        )

        # Layout settings
        fig.update_layout(
            title=high_resolution + ": Averaged RFI Environment at Green Bank Observatory",
            xaxis_title="Frequency (MHz)",
            yaxis_title="Average Intensity (Jy)",
            yaxis=dict(range=[-10, 500]),  # Set y-axis range
            xaxis=dict(range=[start_frequency, end_frequency]),  # Set x-axis range
            showlegend=False,  # No legend for this plot
        )

        # Update figure size
        fig.update_layout(width=900, height=400)

        # Dynamic plot function (using callbacks in Plotly)
        

        
        # Connect callback to relayout events
        

        plot_html = pio.to_html(fig, full_html=False)

        self.plotly(plot_html)

        #fig.show()


        # Display the interactive plot



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

    #string_array = ["TRFI_020423_S1","TRFI_020623_S1","TRFI_020623_S2","TRFI_020723_S1","TRFI_020823_S1"]


    Window.do_plot(screen,
            session = "TRFI_110823_S1",
            high_resolution = user_input,
            receivers = receivers,
            start_date = start_date,
            end_date = end_date,
        )


    sys.exit(app.exec_())
    

if __name__ == "__main__":
    main()



