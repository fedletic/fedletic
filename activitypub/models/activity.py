import logging

import ulid
from django.conf import settings
from django.db import models

log = logging.getLogger(__name__)


class Activity(models.Model):

    actor = models.ForeignKey(
        "activitypub.Actor",
        on_delete=models.CASCADE,
        related_name="activities",
        null=True,
        blank=True,
    )
    target = models.ForeignKey(
        "activitypub.Actor",
        on_delete=models.CASCADE,
        related_name="targeted_activities",
        null=True,
        blank=True,
    )
    id = models.URLField(max_length=1024, primary_key=True)
    activity_type = models.CharField(max_length=50)

    object_uri = models.CharField(null=True, blank=True)
    object_json = models.JSONField(null=True, blank=True)
    additional_fields = models.JSONField(null=True, blank=True)

    context = models.JSONField(null=True, blank=True)
    raw_activity = models.JSONField(null=True, blank=True)
    is_remote = models.BooleanField(default=False)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    @staticmethod
    def create_from_json(actor, activity_data):
        activity_id = activity_data["id"]
        try:
            activity = Activity.objects.get(pk=activity_id)
            log.info("Activity with activity_id=%s already exists.", activity_id)
            return activity
        except Activity.DoesNotExist:
            pass

        log.info("Creating new activity from json with activity_id=%s", activity_id)
        activity_object = activity_data["object"]
        creation_kwargs = {
            "id": activity_id,
            "actor": actor,
            "activity_type": activity_data.get("type"),
            "is_remote": True,
            "context": activity_data.get("@context"),
            "raw_activity": activity_data,
        }

        if isinstance(activity_object, str):
            creation_kwargs["object_uri"] = activity_object
        else:
            creation_kwargs["object_json"] = activity_object

        skip_fields = {"id", "type", "actor", "object", "published", "@context"}
        additional_fields = {}

        for key, value in activity_data.items():
            if key not in skip_fields and value is not None:
                additional_fields[key] = value

        creation_kwargs["additional_fields"] = additional_fields
        return Activity.objects.create(**creation_kwargs)

    @staticmethod
    def create_from_kwargs(
        actor, target, activity_type, activity_object, context=None, **kwargs
    ):
        if not context:
            context = ["https://www.w3.org/ns/activitystreams"]

        activity_id = str(ulid.new())
        activity_id = f"https://{settings.SITE_URL}/activities/{activity_id}"

        creation_kwargs = {}
        additional_fields = {}
        if isinstance(activity_object, str):
            creation_kwargs["object_uri"] = activity_object
        else:
            creation_kwargs["object_json"] = activity_object

        for key, value in kwargs.items():
            additional_fields[key] = value

        return Activity.objects.create(
            id=activity_id,
            actor=actor,
            target=target,
            activity_type=activity_type,
            context=context,
            is_remote=False,
            additional_fields=additional_fields,
            **creation_kwargs,
        )

    def to_activity_json(self):
        result = {
            "@context": self.context or "https://www.w3.org/ns/activitystreams",
            "id": self.id,
            "type": self.activity_type,
        }

        if self.actor:
            result["actor"] = self.actor.actor_url

        # Handle object (either URI or full JSON)
        if self.object_uri:
            result["object"] = self.object_uri
        elif self.object_json:
            result["object"] = self.object_json

        # Add additional fields
        if self.additional_fields:
            for key, value in self.additional_fields.items():
                result[key] = value

        return result
