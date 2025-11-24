import logging

import bleach
import httpx
from django.db.models import F

from activitypub.events import events
from activitypub.models import Activity
from feeds.methods import distribute_to_feed
from workouts.models import Comment, Workout

log = logging.getLogger(__name__)


@events.on("activity")
def process_incoming_activity(activity_id):
    activity = Activity.objects.get(pk=activity_id)
    log.debug(
        "Incoming activity id=%s type=%s",
        activity_id,
        activity.activity_type,
    )

    if not activity.activity_type == "Create":
        # TODO: support update etcetera.
        return

    if not activity.object_json:
        # Not going to do anything with this, as we expect an object to be inside of the Create.
        # TODO: support URIs
        return

    if activity.object_json["type"] == "Workout":
        log.info("Creating incoming workout=%s", activity.object_json)
        activity_object = httpx.get(
            activity.object_json["content"],
            headers={"accept": "application/activity+json"},
        )
        workout = Workout.create_from_activitypub_object(
            ap_object=activity_object.json(), actor=activity.actor
        )
        log.debug("Created new workout")
        distribute_to_feed(source=workout.actor, content_object=workout)

    elif activity.object_json["type"] == "Note":
        log.info("Creating incoming note=%s", activity.object_json)
        ap_uri = activity.object_json.get("inReplyTo")
        if not ap_uri:
            log.warning("Incoming note %s does not have an ap_uri", activity_id)
            return

        ap_uri = "/".join(ap_uri.split("/")[0:-1])
        try:
            workout = Workout.objects.get(ap_uri=ap_uri)
        except Workout.DoesNotExist:
            log.warning(
                "Incoming note %s refers to a workout that does not exist (%s)",
                activity_id,
                ap_uri,
            )
            return

        comment = bleach.clean(activity.object_json["content"], tags=[], strip=True)
        Comment.objects.create(
            actor=activity.actor,
            workout=workout,
            content=comment,
        )
        Workout.objects.filter(pk=workout.pk).update(
            comment_count=F("comment_count") + 1
        )
