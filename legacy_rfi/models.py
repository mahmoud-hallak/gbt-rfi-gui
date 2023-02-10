from django.db import models


class MasterRfiCatalog(models.Model):
    feed = models.IntegerField(blank=True, null=True)
    frontend = models.CharField(max_length=15, blank=True, null=True)
    azimuth_deg = models.DecimalField(
        db_column="azimuth_deg", max_digits=8, decimal_places=5, blank=True, null=True
    )  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    projid = models.CharField(max_length=50, blank=True, null=True)
    resolution_mhz = models.DecimalField(
        db_column="resolution_mhz",
        max_digits=11,
        decimal_places=10,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    window = models.IntegerField(
        db_column="Window", blank=True, null=True
    )  # Field name made lowercase.
    exposure = models.DecimalField(
        max_digits=8, decimal_places=5, blank=True, null=True
    )
    utc_hrs = models.DecimalField(max_digits=8, decimal_places=6, blank=True, null=True)
    date = models.CharField(max_length=10, blank=True, null=True)
    number_if_windows = models.IntegerField(
        db_column="number_IF_Windows", blank=True, null=True
    )  # Field name made lowercase.
    channel = models.IntegerField(
        db_column="Channel", blank=True, null=True
    )  # Field name made lowercase.
    backend = models.CharField(max_length=12, blank=True, null=True)
    mjd = models.DecimalField(max_digits=8, decimal_places=3, blank=True)
    frequency_mhz = models.DecimalField(
        db_column="Frequency_MHz", max_digits=12, decimal_places=4, blank=True
    )  # Field name made lowercase.
    lst = models.DecimalField(max_digits=9, decimal_places=7, blank=True, null=True)
    filename = models.CharField(max_length=100, blank=True, null=True)
    polarization = models.CharField(max_length=1, blank=True, null=True)
    source = models.CharField(max_length=11, blank=True, null=True)
    tsys = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True)
    frequency_type = models.CharField(max_length=4, blank=True, null=True)
    units = models.CharField(max_length=2, blank=True, null=True)
    intensity_jy = models.DecimalField(
        db_column="Intensity_Jy", max_digits=15, decimal_places=6, blank=True, null=True
    )  # Field name made lowercase.
    scan_number = models.IntegerField(blank=True, null=True)
    elevation_deg = models.DecimalField(
        db_column="elevation_deg", max_digits=8, decimal_places=6, blank=True, null=True
    )  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.

    def __str__(self):
        return self.filename

    class Meta:
        unique_togather = (("mjd", "frequency_mhz"),)

    class Meta:
        managed = False
        db_table = "Master_RFI_Catalog"

class processed_projid(models.Model):
    projid = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.filename

    class Meta:
        managed = False
        db_table = "processed_projid"

class bad_files_db(models.Model):
    filename = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.filename

    class Meta:
        managed = False
        db_table = "Bad_files"

class flagged_db(models.Model):
    projid = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.filename

    class Meta:
        managed = False
        db_table = "Master_RFI_Flagged_Catalog"
