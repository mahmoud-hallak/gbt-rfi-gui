import os
import sys

import pandas as pd

# from calculation import *
# from practice import *
from connection import *
from listings.models import MasterRfiCatalog
from mjd import datetime_to_mjd
from PyQt5.Qt import QApplication, QMainWindow
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUiType

from django.db.models import *

# add .Ui file path here
qtCreatorFile = "/users/bgregory/repos/GBT_RFI_Webpage/GBT_RFI_Webpage/python_django_dev/aaron_gui/RFI_Gui_3.ui"
Ui_MainWindow, QtBaseClass = loadUiType(qtCreatorFile)


class App(QMainWindow, Ui_MainWindow):
    def __init__(self):
        # Do QMainWindow stuff
        QMainWindow.__init__(self)
        # Set up the UI file
        self.setupUi(self)
        self.pushButton.clicked.connect(self.clicked)
        self.pushButton2.clicked.connect(self.save_file)
        self.save_df = pd.DataFrame()

    def clicked(self):
        def choose_plot(rcvr, graph1, graph2, range1, range2, time1, time2):
            pass

            rows = MasterRfiCatalog.objects.all()
            rcvr_filt = MasterRfiCatalog.objects.values_list(
                "frontend", flat=True
            ).distinct()
            mjd_date1 = datetime_to_mjd(time1)
            mjd_date2 = datetime_to_mjd(time2)
            abs(mjd_date1 - mjd_date2)

            filtered = rows.filter(frontend=rcvr).filter(
                mjd__gte=mjd_date1, mjd__lte=mjd_date2
            )
            data = pd.DataFrame(filtered.values())

            new_data = data[["mjd", "intensity_jy", "frequency_mhz"]].copy()
            new_data["mjd"] = new_data["mjd"].astype(float, errors="raise")
            new_data["frequency_mhz"] = new_data["frequency_mhz"].astype(
                float, errors="raise"
            )
            new_data["intensity_jy"] = new_data["intensity_jy"].astype(
                float, errors="raise"
            )

            grouped_multiple = new_data.groupby(["mjd", "frequency_mhz"]).agg(
                {"intensity_jy": ["mean"]}
            )
            grouped_multiple.columns = ["intensity_mean"]
            grouped_multiple = grouped_multiple.reset_index()

            if graph1 == True and graph2 == True:
                print("Please pick Broad plot or Specified plot, you cannot pick both")

            elif graph1 == False and graph2 == False:
                print("Please pick Broad plot or Specified plot")

            elif graph1 == True:

                broad_plot(grouped_multiple)
                color_plot(new_data, rcvr, time1, time2)
                self.save_df = self.save_df.append(grouped_multiple, ignore_index=True)

            elif graph2 == True:

                pick_range(grouped_multiple, int(range1), int(range2))

        # signals

        item = self.listWidget.currentItem()
        Receiver = item.text()

        beginning = self.Start_date.dateTime().toPyDateTime()
        end = self.stop_date.dateTime().toPyDateTime()

        full = self.Full_Range.isChecked()
        Specified = self.SpecifiedRange.isChecked()

        Start = self.Start_frequency.toPlainText()
        Stop = self.stop_frequency.toPlainText()

        choose_plot(Receiver, full, Specified, Start, Stop, beginning, end)

    def save_file(self):
        rfi_file_name = self.rfi_file.toPlainText()
        directory_path = self.Save_Data.toPlainText()
        self.save_df.to_csv(
            os.path.join(directory_path, "{}.csv".format(rfi_file_name))
        )
        print("{}.csv file was printed to {}".format(rfi_file_name, directory_path))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())
