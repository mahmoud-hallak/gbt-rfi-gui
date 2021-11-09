from rest_framework import serializers

from legacy_rfi.models import MasterRfiCatalog


class MasterRfiCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterRfiCatalog
        fields = ["frequency_mhz", "intensity_jy"]
