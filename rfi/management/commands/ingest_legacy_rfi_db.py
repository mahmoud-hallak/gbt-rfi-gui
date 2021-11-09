import logging
import re

from tqdm import tqdm

from django.core.management.base import BaseCommand

from legacy_rfi.models import MasterRfiCatalog
from rfi.mjd import mjd_to_datetime
from rfi.models import (
    Backend,
    Coordinates,
    Feed,
    File,
    Frequency,
    FrequencyType,
    Frontend,
    Polarization,
    Project,
    Scan,
    Session,
    Source,
)
from rfi_query.handlers import TqdmLoggingHandler
from rfi_query.utils import ModelCache

BackendCache = ModelCache(Backend)
CoordinatesCache = ModelCache(Coordinates)
FeedCache = ModelCache(Feed)
FileCache = ModelCache(File)
FrequencyTypeCache = ModelCache(FrequencyType)
FrontendCache = ModelCache(Frontend)
PolarizationCache = ModelCache(Polarization)
ProjectCache = ModelCache(Project)
ScanCache = ModelCache(Scan)
SessionCache = ModelCache(Session)
SourceCache = ModelCache(Source)

PROJECT_NAME_REGEX = re.compile(
    r"(?P<type>[AT])?(?P<prefix>[a-zA-Z]*)[^\w]*(?P<year>\d{2,4})(?P<semester>[a-z])[_\s\-/]*"
    r"(?P<code>[^\-_\s]{,10})(?:[_\s\-/]*(?P<session>[^_\s\-/][\w\-]*))?",
    re.IGNORECASE,
)
TEST_PROJECT_NAME_REGEX = re.compile(
    r"(?P<type>T)?(?P<prefix>[A-Z]+)[\-_\s]*(?P<code>)[_\s\-/]+(?P<session>.+)",
    re.IGNORECASE,
)


def parse_archive_project_name(name):
    """Given a project/session name, normalize it the standard MetaProject
    format."""

    parsed = None

    match = PROJECT_NAME_REGEX.match(name)
    if match:
        parsed = match.groupdict()
    else:
        match = TEST_PROJECT_NAME_REGEX.match(name)
        if match:
            parsed = match.groupdict()

    if parsed is None:
        return None

    if "year" in parsed:
        return "{type}{prefix}{year}{semester}_{code}".format(
            type=parsed["type"].upper() if parsed["type"] else "",
            prefix=parsed["prefix"].upper(),
            year=parsed["year"],
            semester=parsed["semester"].upper(),
            code=parsed["code"].upper().rjust(3, "0"),
        )
    return "{type}{prefix}".format(
        type=parsed["type"].upper() if parsed["type"] else "",
        prefix=parsed["prefix"].upper(),
        # session=parsed["session"].upper(),
    )


printed_projects = set()


def db_logging_on():
    logger = logging.getLogger("django.db.backends")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(TqdmLoggingHandler())


def db_logging_off():
    logger = logging.getLogger("django.db.backends")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []


def write_chunk(frequencies, batch_size, chunk_start):
    # tqdm.write(
    #     f"Beginning bulk creation of chunk {chunk_start}: {len(frequencies)} Frequencies"
    # )
    frequencies = Frequency.objects.bulk_create(frequencies, batch_size=batch_size)
    # tqdm.write(
    #     f"Done with bulk creation of chunk {chunk_start}: {len(frequencies)} Frequencies"
    # )
    return frequencies


class Command(BaseCommand):
    help = "Ingest data from the 'old' RFI DB (legacy_rfi app) into the 'new' RFI DB (rfi app)"
    # Don't run Django's automated health checks on each execution
    skip_checks = True

    def handle_row(self, row):
        """Handle a single row from MasterRfiCatalog.

        Each row represents information for a given frequency of a given
        window of a given scan
        """
        full_session_name = row["projid"]
        project_name = parse_archive_project_name(full_session_name)
        # Ensure that project is a substring of full_session_name
        if not project_name:
            project_name = "UNKNOWN"
            full_session_name = "UNKNOWN"
            # tqdm.write(f"WARNING: Unknown project found: {full_session_name}")

        if project_name not in printed_projects:
            tqdm.write(f"Parsed {project_name=} from {full_session_name=}")
            printed_projects.add(project_name)

        project = ProjectCache.get_or_create(project_name, dict(name=project_name))
        file = FileCache.get_or_create(row["filename"], dict(name=row["filename"]))
        session = SessionCache.get_or_create(
            full_session_name, dict(name=full_session_name, project=project, file=file)
        )
        frontend = FrontendCache.get_or_create(
            row["frontend"], dict(name=row["frontend"])
        )
        feed = FeedCache.get_or_create(
            row["feed"], dict(number=row["feed"], frontend=frontend)
        )
        backend = BackendCache.get_or_create(row["backend"], dict(name=row["backend"]))
        coordinates = CoordinatesCache.get_or_create(
            (row["azimuth_deg"], row["elevation_deg"]),
            dict(azimuth=row["azimuth_deg"], elevation=row["elevation_deg"]),
        )
        source = SourceCache.get_or_create(row["source"], dict(name=row["source"]))
        frequency_type = FrequencyTypeCache.get_or_create(
            row["frequency_type"], dict(name=row["frequency_type"])
        )
        polarization = PolarizationCache.get_or_create(
            row["polarization"], dict(name=row["polarization"])
        )

        scan = ScanCache.get_or_create(
            # Scan number appears to be wrong, but MJD is always(?) set per-scan,
            # so we use both to ensure uniqueness
            (full_session_name, row["scan_number"], row["mjd"]),
            dict(
                session=session,
                feed=feed,
                frontend=frontend,
                backend=backend,
                coordinates=coordinates,
                source=source,
                frequency_type=frequency_type,
                polarization=polarization,
                number=row["scan_number"],
                mjd=row["mjd"],
                lst=row["lst"],
                resolution=row["resolution_mhz"],
                exposure=row["exposure"],
                tsys=row["tsys"],
                unit=row["units"],
                datetime=mjd_to_datetime(row["mjd"]),
            ),
        )
        if not str(row["window"]).isnumeric():
            # tqdm.write(f"Window number is non-numeric: {row["window"]}; substituting 0")
            row["window"] = 0
        if not str(row["channel"]).isnumeric():
            # tqdm.write(f"Channel number is non-numeric: {row["channel"]}; substituting 0")
            row["channel"] = 0
        frequency = Frequency(
            scan_id=scan.id,
            window=row["window"],
            channel=row["channel"],
            frequency=row["frequency_mhz"],
            intensity=row["intensity_jy"],
        )
        return frequency

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of rows that are processed",
        )
        parser.add_argument(
            "--offset",
            type=int,
            help="Offset the start row",
        )
        parser.add_argument(
            "-r",
            "--read-chunk-size",
            type=int,
            help="Set the size of each chunk that is fetched from MasterRfiCatalog",
            default=20000,
        )
        parser.add_argument(
            "-w",
            "--write-chunk-size",
            type=int,
            help="Set the size of each chunk that is written to 'new' DB",
            default=20000,
        )
        parser.add_argument("--sql", action="store_true", help="Print all SQL queries")
        parser.add_argument(
            "--no-progress", action="store_true", help="Don't show progress bars"
        )

    def handle_rows(
        self, rows, num_rows, read_chunk_size, write_chunk_size, progress=False
    ):
        progress = tqdm(total=num_rows, unit="row", smoothing=0, disable=not progress)
        for chunk_start in range(0, num_rows, read_chunk_size):
            frequencies = []
            for row in rows[chunk_start : chunk_start + read_chunk_size]:
                frequencies.append(self.handle_row(row))
                # progress.update()

            write_chunk(frequencies, write_chunk_size, chunk_start)
            progress.update(read_chunk_size)

    def handle(self, *args, **options):
        tqdm.write("init")
        if options["sql"]:
            db_logging_on()

        read_chunk_size = options["read_chunk_size"]
        write_chunk_size = options["write_chunk_size"]
        # Get out only the values we need
        rows = MasterRfiCatalog.objects.values(
            "azimuth_deg",
            "backend",
            "channel",
            "elevation_deg",
            "exposure",
            "feed",
            "filename",
            "frequency_mhz",
            "frequency_type",
            "frontend",
            "intensity_jy",
            "lst",
            "mjd",
            "polarization",
            "projid",
            "resolution_mhz",
            "scan_number",
            "source",
            "tsys",
            "units",
            "window",
        )
        if options["offset"]:
            print(f"Offsetting start row by {options['offset']}")
            rows = rows[options["offset"] :]

        num_rows = rows.count()
        tqdm.write(
            f"Fetching {num_rows} rows from MasterRfiCatalog in chunks of {read_chunk_size}"
        )
        self.handle_rows(
            rows,
            num_rows,
            read_chunk_size,
            write_chunk_size,
            not options["no_progress"],
        )

        print(BackendCache)
        print(CoordinatesCache)
        print(FeedCache)
        print(FileCache)
        print(FrequencyTypeCache)
        print(FrontendCache)
        print(PolarizationCache)
        print(ProjectCache)
        print(ScanCache)
        print(SessionCache)
        print(SourceCache)
