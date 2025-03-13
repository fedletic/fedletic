import datetime

from ninja.security import HttpBearer
from oauth2_provider.models import AccessToken
from oauth2_provider.settings import oauth2_settings


class OAuth2BearerToken(HttpBearer):
    def authenticate(self, request, token):
        """
        Authenticate the request, given the token.
        """
        try:
            # Find the token in the database
            access_token = AccessToken.objects.select_related("user")
            access_token = access_token.get(token=token)

            # Check if the token is expired
            if access_token.expires < datetime.datetime.now():
                return None

            # Check if token has required scopes
            # This is similar to how TokenHasReadWriteScope would work
            required_scopes = getattr(
                self, "required_scopes", oauth2_settings.READ_SCOPE
            )
            if required_scopes:
                # Parse the scopes from the token
                token_scopes = access_token.scope.split()

                # Check if the token has the required scopes
                if not set(required_scopes).issubset(set(token_scopes)):
                    return None

            # Return the user from the token
            return access_token.user

        except AccessToken.DoesNotExist:
            return None
