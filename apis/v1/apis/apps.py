import ulid
from django.utils.crypto import get_random_string
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apis.models import OAuth2Application
from apis.v1.serializers.apps import AppCreateSerializer


class AppsAPI(mixins.CreateModelMixin, viewsets.GenericViewSet):

    queryset = OAuth2Application.objects.all()
    serializer_class = AppCreateSerializer

    def get_permissions(self):
        return [AllowAny()]

    def create(self, request, *args, **kwargs):
        """
        Register a new OAuth application.

        This endpoint mirrors Mastodon's /api/v1/apps endpoint for registering OAuth clients.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Generate client ID and secret
        client_id = str(ulid.new()).lower()
        client_secret = get_random_string(128)

        # Create corresponding oauth2_provider Application
        OAuth2Application.objects.create(
            name=serializer.validated_data["name"],
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=serializer.validated_data.get("redirect_uris", ""),
            client_type=OAuth2Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=OAuth2Application.GRANT_AUTHORIZATION_CODE,
            website=serializer.validated_data.get("website", None),
        )

        # Return the serialized app with client ID and secret
        # We only return this _once_.
        return Response(
            {
                "client_id": client_id,
                "client_secret": client_secret,
            },
            status=status.HTTP_201_CREATED,
        )
