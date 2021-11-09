from rest_framework import serializers

from rfi.models import MasterRfiCatalog


class MasterRfiCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterRfiCatalog
        fields = ["frequency_mhz", "intensity_jy"]
