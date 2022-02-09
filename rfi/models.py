from django.db import models


# From column 'backend'
class Backend(models.Model):
    name = models.TextField(unique=True, db_index=True)

    def __str__(self):
        return f"{self.name}"


# From column 'frontend'
class Frontend(models.Model):
    name = models.TextField(unique=True, db_index=True)

    def __str__(self):
        
        return f"{self.name}"


# Derived from 'projid' column
class Project(models.Model):
    name = models.TextField(unique=True, db_index=True)

    def __str__(self):
        return f"{self.name}"


# From from 'projid' column
class Session(models.Model):
    name = models.TextField(unique=True, db_index=True)
    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        help_text="The Project this Session belongs to",
    )
    # NOTE: This might not turn out to be 1:1, but let's try
    file = models.OneToOneField(
        "File",
        on_delete=models.CASCADE,
        help_text="The FITS file this Session data was pulled from",
    )
    # From column 'counts' (unclear what this is)
    # NOTE: Seems unused
    # counts = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        unique_together = ("project", "name")


class Scan(models.Model):
    session = models.ForeignKey("Session", on_delete=models.CASCADE)
    feed = models.ForeignKey("Feed", on_delete=models.CASCADE)
    frontend = models.ForeignKey("Frontend", on_delete=models.CASCADE)
    backend = models.ForeignKey("Backend", on_delete=models.CASCADE)
    coordinates = models.ForeignKey(
        "Coordinates",
        on_delete=models.CASCADE,
        help_text="The averaged(?) location on the sky this scan took place",
    )
    source = models.ForeignKey("Source", on_delete=models.CASCADE)
    frequency_type = models.ForeignKey("FrequencyType", on_delete=models.CASCADE)
    polarization = models.ForeignKey("Polarization", on_delete=models.CASCADE)

    number = models.PositiveIntegerField()
    mjd = models.DecimalField(max_digits=8, decimal_places=3, db_index=True)
    datetime = models.DateTimeField(null=True, db_index=True)
    lst = models.DecimalField(max_digits=9, decimal_places=7)
    resolution = models.DecimalField(max_digits=11, decimal_places=10)
    exposure = models.DecimalField(max_digits=8, decimal_places=5)
    tsys = models.DecimalField(max_digits=6, decimal_places=4)
    unit = models.TextField()

    def __str__(self):
        return f"{self.session.name} #{self.number}"

    class Meta:
        unique_together = ("session", "number", "mjd")


# class Window(models.Model):
#     scan = models.ForeignKey("Scan", on_delete=models.CASCADE)
#     number = models.PositiveIntegerField()

#     class Meta:
#         unique_together = ("scan", "number")

#     def __str__(self):
#         return (
#             f"{self.scan.session.name}: Scan #{self.scan.number}: "
#             f"Window #{self.number}"
#         )


class Frequency(models.Model):
    scan = models.ForeignKey("Scan", on_delete=models.CASCADE)
    window = models.PositiveIntegerField()
    channel = models.PositiveIntegerField()
    frequency = models.FloatField()
    intensity = models.FloatField(help_text="Intensity in Jy")

    class Meta:
        unique_together = ("scan", "channel", "frequency")

    def __str__(self):
        return (
            f"{self.scan.session.name}: Scan #{self.scan.number}: "
            f"Channel #{self.channel}: Frequency: {self.frequency} MHz "
            f" Intensity: {self.intensity} Jy"
        )


# TODO: Prefix all names with /home/www.gb.nrao.edu/content/IPG/rfiarchive_files/GBTDataImages/
# From column 'filename'
class File(models.Model):
    name = models.TextField(unique=True, db_index=True)
    path = models.TextField(unique=True, db_index=True)

    def __str__(self):
        return f"{self.name}"


# From column 'polarization'
class Polarization(models.Model):
    name = models.TextField(unique=True, db_index=True)

    def __str__(self):
        return f"{self.name}"


# From column 'source'
class Source(models.Model):
    name = models.TextField(unique=True, db_index=True)

    def __str__(self):
        return f"{self.name}"


class Feed(models.Model):
    # From column 'feed'
    # Values: 0 1 or 2
    # NOTE: If there is more information about a feed that we need to track (other than its number)
    #       then make this its own Model
    number = models.PositiveIntegerField()
    frontend = models.ForeignKey("Frontend", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("number", "frontend")


# From column 'frequency_type'
class FrequencyType(models.Model):
    name = models.TextField(unique=True, db_index=True)

    def __str__(self):
        return f"{self.name}"


# From columns 'azimuth_deg' and 'elevation_deg'
class Coordinates(models.Model):
    azimuth = models.DecimalField(
        max_digits=8, decimal_places=5, help_text="Azimuth in degrees"
    )
    elevation = models.DecimalField(
        max_digits=8, decimal_places=6, help_text="Elevation in degrees"
    )

    class Meta:
        unique_together = ("azimuth", "elevation")
