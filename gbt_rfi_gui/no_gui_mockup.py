import datetime
import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rfi_query.settings")
import django
django.setup()

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from rfi.models import Frequency, Scan

# timing
import time
from datetime import datetime, timedelta

'''
# TIMING RESOURCES
https://realpython.com/python-timer/
https://www.geeksforgeeks.org/time-command-in-linux-with-examples/

# KASEY'S TEST SESSION
time python no_gui_mockup.py TRFI_110823_S1

# PROFILING
https://docs.python.org/3/library/profile.html

you can do this yourself:
```
$ time python -m cProfile -o profile.out "no_gui_mockup.py" TRFI_110823_S1
```

That should work, and produce a `profile.out` file
Then you can `pip install snakeviz`
then `$ snakeviz profile.out -b firefox` 
'''

class TimingTests():
    def __init__(self, session):
        # set up the timing via time.time() 
        ## going to use t1 and t2
        self.t1 = time.time()

        # set up timing via perf_counter()
        ## look for tik and tok
        self.tok = time.perf_counter()

        # set up timing via datetime
        # start and end
        self.start = datetime.now()


        self.do_plot(session)

    def do_plot(self, session):
        # don't want to look at dates with no data, find the most recent session date
        qs = Frequency.objects.filter(scan__session__name=session)

        # make a 4 column dataFrame for the data needed to plot
        data = pd.DataFrame(
            qs.values("frequency", "intensity", "scan__datetime", "scan__session__name")
        )

        start_frequency = data["frequency"].min()
        end_frequency = data["frequency"].max()

        if not data.empty:
            # line plot
            self.make_plot(data, start_frequency, end_frequency)

        else:
            print("No data found")


    def make_plot(self, data, start_frequency, end_frequency):
        # make a new object with the average intensity for the 2D plot
        mean_data_intens = data.groupby(
            ["scan__datetime", "frequency", "scan__session__name"]
        ).agg({"intensity": ["mean"]})
        mean_data_intens.columns = ["intensity_mean"]
        mean_data = mean_data_intens.reset_index()
        # sort values so the plot looks better, this has nothing to do with the actual data
        sorted_mean_data = mean_data.sort_values(by=["frequency", "intensity_mean"])

        # generate the description fro the plot
        txt = f" \
            Your data summary for this plot: \n \
            Frequency Range : {mean_data['frequency'].min()}MHz to {mean_data['frequency'].max()}MHz "

        # print out info for investagative GBO scientists
        print("Your requested projects are below:")
        print("Session Date \t\t Project_ID")
        print("-------------------------------------")
        sort_by_date = sorted_mean_data.sort_values(by=["scan__session__name"])
        project_ids = sort_by_date["scan__session__name"].unique()
        for i in project_ids:
            proj_date = sort_by_date[
                sort_by_date["scan__session__name"] == i
            ].scan__datetime.unique()
            proj_date = proj_date.strftime("%Y-%m-%d")
            print(f"", proj_date[0], "\t\t", str(i))

        # Create the 2D line plot
        fig, ax = plt.subplots(1, figsize=(9, 4))
        plt.title(txt, fontsize=8)
        plt.suptitle("Averaged RFI Environment at Green Bank Observatory")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Average Intensity (Jy)")
        plt.ylim(-10, 500)
        plt.xlim(start_frequency, end_frequency)

        # Plot one or both the line plot and the annotations
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

        plt.show(block=False)
        plt.pause(0.0001)
        plt.close()

        # for the time tests
        t2 = time.time()
        print("\n \nThe time method tells us the time to run  is: %.4f seconds" % (t2-self.t1))

        # for the perf_countertests
        tik = time.perf_counter()
        print("\n \nThe perf_counter method tells us the time to run is: %.4f seconds" % (tik-self.tok))

        # for the datetime tests
        end = datetime.now()
        print("\n \nThe datetime method tells us the time to run is: ", end-self.start, "seconds")

if __name__ == "__main__":
    session = sys.argv[1]
    timeTests = TimingTests(session)