from django.db import models

from activitypub.utils import generate_ulid

from .activity import Activity  # noqa: F401
from .actor import Actor  # noqa: F401
from .follower import Follower  # noqa: F401


class ActivityPubBaseModel(models.Model):

    id = models.CharField(
        primary_key=True, max_length=26, default=generate_ulid, editable=False
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    actor = models.ForeignKey(
        "activitypub.Actor",  # Assumes an Actor model exists
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activitypub_objects",
    )

    class Meta:
        abstract = True  # This is a base model, not a table itself
