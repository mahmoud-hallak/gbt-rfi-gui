import os

import pprint
from django.db import connection


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rfi_query.settings")

import django

django.setup()

from rfi.models import Frequency


print(connection.settings_dict)

print(pprint.pformat(connection.settings_dict))


qs = Frequency.objects.all()

#qs = qs.filter(view_level_0=True)