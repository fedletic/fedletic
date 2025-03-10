import logging

from celery import shared_task
from celery.contrib.django.task import DjangoTask
from django.db import IntegrityError

from activitypub.events import events
from activitypub.models.activity import Activity
from activitypub.models.actor import Actor
from activitypub.models.follower import Follower
from activitypub.tasks.publish_activity import publish_activity
from activitypub.utils import webfinger_from_url

log = logging.getLogger(__name__)


def process_follow(activity):
    if activity.activity_type == "Follow":
        actor = activity.actor
        target = Actor.objects.get(
            webfinger=webfinger_from_url(actor_url=activity.object_uri)
        )

        try:
            Follower.objects.create(
                actor=actor,
                target=target,
            )
        except IntegrityError:
            log.info(
                "Follower relation between actor=%s and target=%s already exists",
                actor,
                target,
            )

        accept_activity = Activity.create_from_kwargs(
            actor=target,
            target=actor,
            context="https://www.w3.org/ns/activitystreams",
            activity_type="Accept",
            activity_object={
                "id": activity.id,
                "type": "Follow",
                "actor": actor.actor_url,
                "object": target.actor_url,
            },
        )
        publish_activity.delay_on_commit(accept_activity.pk)


def process_unfollow(activity):

    actor = activity.actor
    target = Actor.objects.get(actor_url=activity.object_json["object"])

    log.info("Unfollowing actor=%s target=%s", actor, target)

    Follower.objects.filter(
        actor=actor,
        target=target,
    ).delete()

    # Create activity to undo.
    accept_undo_activity = Activity.create_from_kwargs(
        actor=target,
        target=actor,
        context="application/activity+json",
        activity_type="Undo",
        activity_object={
            "id": activity.id,
            "type": "Follow",
            "actor": actor.actor_url,
            "object": target.actor_url,
        },
    )

    publish_activity.delay_on_commit(accept_undo_activity.pk)


@shared_task(base=DjangoTask)
def process_activity(activity_id):
    """
    This is for incoming (non-local) activities only.
    """
    activity = Activity.objects.get(pk=activity_id)

    log.info("Processing activity=%s content=%s", activity.id, activity.object_json)
    if activity.activity_type == "Follow":
        process_follow(activity)

    if activity.activity_type == "Undo":
        obj_type = activity.object_json["type"]
        if obj_type == "Follow":
            process_unfollow(activity=activity)

    events.fire(events.EVENT_ACTIVITY, activity_id=activity_id)
