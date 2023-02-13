import os

import pandas as pd

from django.core.management.base import BaseCommand

from legacy_rfi.models import (
    MasterRfiCatalog,
    bad_files_db,
    flagged_db,
    processed_projid,
)


class DuplicateValues(Exception):
    pass


class Command(BaseCommand):
    help = "Upload data from the reduced txt files to the old DB (legacy_rfi_app)"

    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--single-file",
            type=str,
            help="Upload just one known file in GBTDataImages, provide just file name",
        )

    def handle(self, *args, **options):
        self.directory = (
            "/home/www.gb.nrao.edu/content/IPG/rfiarchive_files/GBTDataImages/"
        )
        self.problem_files = []  # for a error report at the end

        # want the option to not ahve to run over the whole directory if we know the new filename
        if options["single_file"]:
            self.session = options["single_file"]
            # doing the same steps from here on out
            if self.test_duplicate():
                self.compile_data()
                self.add_to_processed_db()
        else:
            # otherwise iterate over all the files in the data dir to see if they are new
            for self.session in os.listdir(self.directory):
                # Try reading the file's data and header
                projTypes = ["TRFI_", "AGBT"]
                try:
                    # we don't want to try to upload the gif files, saves time
                    if self.session[-4:] == ".txt":
                        if any(ext in self.session for ext in projTypes):
                            if self.test_duplicate():
                                self.compile_data()
                                self.add_to_processed_db()
                        else:
                            print(f"{self.session} is not a recognized session type")
                except:
                    self.problem_files.append(self.session)
                    print(f"Error uploading: {self.session}")

        print(f"These are the problem files, if any: {self.problem_files}")

    def test_duplicate(self):
        # has this scan been, or attempted to have been, uploaded to the DB?

        # only want part of the session name
        self.projid = self.session[:14]

        # using this seperate DB instead of the Mast* DB will save ~1.5 min per call here
        if processed_projid.objects.filter(projid=self.projid).exists():
            print(f"{self.projid} already in the DB. Moving on...")
            return 0
        elif bad_files_db.objects.filter(filename=self.session).exists():
            print(f"{self.projid} in the bad files DB. Moving on...")
            self.problem_files.append(self.session)
            return 0
        elif flagged_db.objects.filter(projid=self.projid).exists():
            print(f"{self.projid} in the flagged files DB. Moving on...")
            self.problem_files.append(self.session)
            return 0
        else:
            print(f"Not in the legacy DB. Uploading session {self.projid} now.")
            return 1

    def compile_data(self):
        header = self.parse_header()
        data = self.parse_data()
        for index, row in header.iterrows():
            data[row["names"]] = row["data"]

        # drop any missing values
        data = data.dropna()

        self.upload_sessions(data)

    def parse_header(self):
        header_rows = pd.read_table(
            self.directory + self.session,
            delimiter=":",
            names=["names", "data"],
            skiprows=1,
            nrows=30,
        )

        # it is frustrating to import a txt file because there can be variations,
        ## ie. scna_number on mult lines or spurious number_of_windows value
        data_string = "################   Data  ################"
        header_rows = header_rows[
            : header_rows[header_rows["names"] == data_string].index[0]
        ]

        for i in header_rows["names"]:
            header_rows["names"] = header_rows["names"].replace(
                i, i.split(" ")[1].strip()
            )

        change_values = {
            "utc": "utc_hrs",
            "scan_numbers": "scan_number",
            "number_IF_Windows": "number_if_windows",
            "frequency_resolution": "resolution_mhz",
            "azimuth": "azimuth_deg",
            "elevation": "elevation_deg",
        }
        for key, value in change_values.items():
            header_rows["names"] = header_rows["names"].replace(key, value)

        # check for the validity of scan_number, if >1 value make it 0
        if len(header_rows.loc[5, "data"].strip().split(" ")) > 1:
            header_rows.loc[5, "data"] = "0"
            # drop any missing values, safe to assume it is scan number lines
            header_rows = header_rows.dropna()

        for i in header_rows["data"]:
            header_rows["data"] = header_rows["data"].replace(i, i.strip())

        return header_rows

    def parse_data(self):
        col_specs = specs_test = [(9, 10), (16, 19), (25, 35), (35, 50)]
        data_rows = pd.read_fwf(
            self.directory + self.session,
            skiprows=22,
            names=["window", "channel", "frequency_mhz", "intensity_jy"],
            index_col=False,
            colspecs=col_specs,
        )
        data_rows = data_rows.dropna()

        return data_rows

    def upload_sessions(self, data):
        print(f"Uploading {len(data.index)} lines for session {self.projid}")
        # parse from df, upload in chunks of 10,000
        chunk_size = 10000
        for i in range(0, len(data.index), chunk_size):
            sessions_data = []
            for index, s in data.iloc[i : i + chunk_size].iterrows():
                sessions_data.append(
                    MasterRfiCatalog(
                        window=s.window,
                        channel=s.channel,
                        frequency_mhz=float(s.frequency_mhz) * 1000,
                        intensity_jy=s.intensity_jy,
                        projid=s.projid,
                        date=s.date,
                        utc_hrs=s.utc_hrs,
                        mjd=s.mjd,
                        lst=s.lst,
                        scan_number=s.scan_number,
                        frontend=s.frontend,
                        feed=s.feed,
                        polarization=s.polarization,
                        backend=s.backend,
                        exposure=s.exposure,
                        tsys=s.tsys,
                        frequency_type=s.frequency_type,
                        resolution_mhz=s.resolution_mhz,
                        source=s.source,
                        azimuth_deg=s.azimuth_deg,
                        elevation_deg=s.elevation_deg,
                        units=s.units,
                        filename=self.session,
                    )
                )
            uploaded_sessions = MasterRfiCatalog.objects.bulk_create(
                sessions_data, batch_size=chunk_size
            )

    def add_to_processed_db(self):
        print(f"Successfully uploaded {self.projid}!")
        processed_projid.objects.create(projid=self.projid)
