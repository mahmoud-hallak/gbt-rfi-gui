from django.core.management.base import BaseCommand

import numpy as np
import pandas as pd
from scipy.signal import find_peaks


from rfi.models import (
	Frequency
)

class Command(BaseCommand):
	help = ""

	requires_system_checks = []

	def add_arguments(self,parser):
		parser.add_argument(
			"sessions", nargs="*", help="The sessions for which to apply the backfill. If blank, backfill all"
			)

		parser.add_argument(
			"--reset", action="store_true", help="Set all Frequency rows to is_peak=False before finding peaks. For dev only"
			)


	def handle(self, sessions, reset: bool, *args, **options):



	    qs = Frequency.objects.all()

	    if(sessions):
	    	
	    	qs = qs.filter(scan__session__name__in=sessions)

	    	
    		if len(qs.values_list("scan__session__name",flat=True).distinct()) != len(set(sessions)):
    			raise ValueError("either dup sessions or not found in db")

	    if reset:
	    	qs.update(view_level_0=False)
	    	qs.update(view_level_1=False)
	    	qs.update(view_level_2=False)
	    	qs.update(view_level_3=False)


	    data = pd.DataFrame(
	        qs.values("id","frequency", "intensity", "scan__session__name")
	    )

	    stuff= Frequency()._meta

	    fields = stuff.get_fields()

	    # Extract and print the names of the fields
	    field_names = [field.name for field in fields]
	    print(field_names)

	    #simplfied view
	    view_level_0 = self.data_filter(1250, data)

	    updated_count = Frequency.objects.filter(id__in=view_level_0["id"]).update(view_level_0=True)

	    print("level 0")
	    print(qs.filter(view_level_0=True).count())

	    data_len = qs.count()
	               

	    #0.1% of the data
	    view_level_1 = self.data_filter(data_len*0.009, data)

	    updated_count = Frequency.objects.filter(id__in=view_level_1["id"]).update(view_level_1=True)

	    print("level 1")
	    print(qs.filter(view_level_1=True).count())


	    #5% of data
	    view_level_2 = self.data_filter(data_len*0.04, data)
	    updated_count = Frequency.objects.filter(id__in=view_level_2["id"]).update(view_level_2=True)
	    print("level 2")
	    print(qs.filter(view_level_2=True).count())


	    view_level_3 = self.data_filter(data_len*0.10, data)
	    updated_count = Frequency.objects.filter(id__in=view_level_3["id"]).update(view_level_3=True)
	    print("level 3")
	    print(qs.filter(view_level_3=True).count())

	    #if len(view_level_0) != updated_count:
	    #	raise AssertionError(f"{len(freq_index)} != {updated_count}")


	    #print(f"Updated {updated_count} records")

	    

	def data_filter(self, points, data):

	    # Specifies a threshold of useful points
	    intensity_threshold = np.median(data["intensity"]) * 5

	    """
	    conversions needed for the plot every other point commands below
	    """
	    windowsize = 1080
	    total_points = len(data["intensity"])

	    points_per_pxl = total_points / windowsize

	    asigned_pt_per_pxl = points / windowsize

	    # every what point to reach a point density asigned
	    every_point = int(points_per_pxl / asigned_pt_per_pxl)

	    # selects the points with the highest intensity within a specified range and intensity
	    peaks, _ = find_peaks(
	        data["intensity"], height=intensity_threshold, distance=every_point
	    )

	    peaks_data = data.iloc[peaks]

	    # creates the simplified dataset (This keeps the graph from losing the zero markers)
	    low_res_data = data.iloc[::every_point]

	    # adds the high resolution peaks to the simplified dataset and sorts them
	    filtered_data = pd.concat([peaks_data, low_res_data]).sort_values(
	        by="frequency"
	    )

	    #Print(len(filtered_data))

	    return filtered_data

