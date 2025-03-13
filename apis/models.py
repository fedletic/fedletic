from django.db import models
from oauth2_provider.models import AbstractApplication

from activitypub.utils import generate_ulid


# Create your models here.
class OAuth2Application(AbstractApplication):
    id = models.CharField(primary_key=True, default=generate_ulid, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    website = models.URLField(null=True, blank=True)
