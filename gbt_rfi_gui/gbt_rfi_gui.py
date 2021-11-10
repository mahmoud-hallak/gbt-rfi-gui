import os
import sys
from datetime import datetime, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rfi_query.settings")

import django

django.setup()

import matplotlib.pyplot as plt
import pandas as pd
import pytz
from PyQt5 import QtGui, QtWidgets

from rfi.models import Frequency, Frontend, Scan


class Window(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        self.form_groupbox = QtWidgets.QGroupBox("Info")
        form = QtWidgets.QFormLayout()

        MAX_TIME_RANGE = timedelta(days=30)

        # List of receivers
        self.receivers = QtWidgets.QListWidget()
        self.receivers.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.receivers.addItems(list(Frontend.objects.values_list("name", flat=True)))
        form.addRow(QtWidgets.QLabel("Receivers:"), self.receivers)

        # Start and Stop Date DateEdit widgets
        self.start_date = QtWidgets.QDateEdit(calendarPopup=True)
        self.start_date.setDate(datetime.today() - timedelta(MAX_TIME_RANGE))
        form.addRow(QtWidgets.QLabel("Start Date:"), self.start_date)

        self.end_date = QtWidgets.QDateEdit(calendarPopup=True)
        self.end_date.setDate(datetime.today())
        form.addRow(QtWidgets.QLabel("End Date:"), self.end_date)

        # Frequency Range
        self.start_frequency = QtWidgets.QLineEdit(self)
        self.start_frequency.setValidator(QtGui.QDoubleValidator())
        form.addRow(QtWidgets.QLabel("Start Freq. (MHz):"), self.start_frequency)

        self.end_frequency = QtWidgets.QLineEdit(self)
        self.end_frequency.setValidator(QtGui.QDoubleValidator())
        form.addRow(QtWidgets.QLabel("End Freq. (MHz):"), self.end_frequency)
        self.form_groupbox.setLayout(form)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.form_groupbox)

        # Push Button to get data
        self.plot_button = QtWidgets.QPushButton(self)
        self.plot_button.setText("Plot")
        layout.addWidget(self.plot_button)
        self.plot_button.clicked.connect(self.clicked)

    def get_scans(
        self, receivers, start_date, end_date, start_frequency, end_frequency
    ):
        qs = Scan.objects.all()
        if receivers:
            print(f"Filtering by {receivers=}")
            qs = qs.filter(frontend__name__in=receivers)

        if start_date:
            print(f"Filtering by {start_date=}")
            qs = qs.filter(datetime__gte=start_date)

        if end_date:
            print(f"Filtering by {end_date=}")
            qs = qs.filter(datetime__lte=end_date)

        if start_frequency:
            print(f"Filtering by {start_frequency=}")
            qs = qs.filter(frequency__frequency__gte=start_frequency)

        if end_frequency:
            print(f"Filtering by {end_frequency=}")
            qs = qs.filter(frequency__frequency__lte=end_frequency)

        return qs

    def do_plot(self, receivers, start_date, end_date, start_frequency, end_frequency):
        qs = Frequency.objects.all()
        if receivers:
            print(f"Filtering by {receivers=}")
            qs = qs.filter(scan__frontend__name__in=receivers)

        if start_date:
            print(f"Filtering by {start_date=}")
            qs = qs.filter(scan__datetime__gte=start_date)

        if end_date:
            print(f"Filtering by {end_date=}")
            qs = qs.filter(scan__datetime__lte=end_date)

        if start_frequency:
            print(f"Filtering by {start_frequency=}")
            qs = qs.filter(frequency__gte=start_frequency)

        if end_frequency:
            print(f"Filtering by {end_frequency=}")
            qs = qs.filter(frequency__lte=end_frequency)

        data = pd.DataFrame(qs.values("frequency", "intensity"))
        if not data.empty:
            plt.title("RFI Data Plot")
            plt.xlabel("Frequency (MHZ)")
            plt.ylabel("Intensity (Jy)")
            plt.plot(data["frequency"], data["intensity"])
            plt.show()
        else:
            QtWidgets.QMessageBox.information(
                self,
                "No Data Found",
                "There is no data for the given filters",
                QtWidgets.QMessageBox.Ok,
            )

    def clicked(self):
        receivers = [i.text() for i in self.receivers.selectedItems()]
        end_date = self.end_date.dateTime().toPyDateTime().replace(tzinfo=pytz.UTC)
        start_date = self.start_date.dateTime().toPyDateTime().replace(tzinfo=pytz.UTC)
        if (end_date - start_date) > MAX_TIME_RANGE:
            start_date = end_date - MAX_TIME_RANGE

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
            start_date=start_date,
            end_date=end_date,
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
