import os
import sys
from datetime import datetime, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rfi_query.settings")

import django

django.setup()

import matplotlib.pyplot as plt
import pandas as pd
import pytz
from astropy.time import Time
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

        self.MAX_TIME_RANGE = timedelta(days=30)

        # List of receivers
        self.receivers.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.receivers.addItems(list(Frontend.objects.values_list("name", flat=True)))

        # Start and Stop Date DateEdit widgets
        self.target_date.setDate(datetime.today())

        # Frequency Range
        self.start_frequency.setValidator(QtGui.QDoubleValidator())
        self.end_frequency.setValidator(QtGui.QDoubleValidator())

        # Push Button to get data
        self.plot_button.clicked.connect(self.clicked)

        # connect menus
        self.actionQuit.triggered.connect(self.menuQuit)
        self.actionAbout.triggered.connect(self.menuAbout)

    def get_scans(self, receivers, target_date, start_frequency, end_frequency):
        most_recent_session_prior_to_target_datetime = (
            Scan.objects.filter(datetime__lte=target_date)
            .order_by("-datetime")
            .first()
            .session
        )
        qs = Scan.objects.filter(
            scan__session=most_recent_session_prior_to_target_datetime
        )
        # qs = Scan.objects.all()
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
        def make_mjd(times):
            t = Time(times)
            return t.mjd

        most_recent_session_prior_to_target_datetime = (
            Scan.objects.filter(datetime__lte=target_date)
            .order_by("-datetime")
            .first()
            .datetime
        )

        print(
            f"Most recent session date: {most_recent_session_prior_to_target_datetime.date()}"
        )
        # qs = Frequency.objects.filter(scan__session=most_recent_session_prior_to_target_datetime)
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

        data = pd.DataFrame(qs.values("frequency", "intensity"))
        # times_mjd = make_mjd(pd.DataFrame(qs.values("scan__datetime")))

        if not data.empty:
            # Plot the 2D graph
            plt.title("RFI Environment at Green Bank Observatory")
            plt.xlabel("Frequency MHz")
            plt.ylabel("Intensity Jy")
            plt.plot(data["frequency"], data["intensity"], color="black", linewidth=0.5)
            plt.show()

            # Plot the color map graph
            """
            fig = plt.figure()
            ax=fig.gca()
            im = ax.imshow((np.log(times_mjd), np.log(data['frequency']), np.log(data['intensity'])))
            cbar = fig.colorbar(im)
            cbar.set_label("log intensity")
            plt.show()
            """

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
