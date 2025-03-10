from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class FeedItem(models.Model):
    source = models.ForeignKey(
        "activitypub.Actor", related_name="+", on_delete=models.CASCADE
    )
    target = models.ForeignKey(
        "activitypub.Actor", related_name="feed_items", on_delete=models.CASCADE
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    created_on = models.DateTimeField(auto_now_add=True)
