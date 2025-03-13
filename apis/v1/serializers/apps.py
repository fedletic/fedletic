from rest_framework import serializers

from apis.models import OAuth2Application


class AppCreateSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="name")
    redirect_uri = serializers.CharField(
        source="redirect_uris", required=False, allow_blank=True
    )
    website = serializers.URLField(required=False, allow_null=True)

    class Meta:
        model = OAuth2Application
        fields = ["client_name", "redirect_uri", "website"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Add the client_id and client_secret to the response
        ret["client_id"] = instance.client_id
        ret["client_secret"] = instance.client_secret
        return ret
