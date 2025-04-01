import datetime
import logging

from activitypub.models import Actor

from .models import FeedItem

log = logging.getLogger(__name__)


def distribute_to_feed(source: Actor, content_object):
    log.debug(
        "Distributing content_object=%s to followers of actor=%s",
        content_object,
        source,
    )

    published_on = (
        content_object.created_on
        if content_object.created_on
        else datetime.datetime.now()
    )

    for follower in source.followers.all():
        # Skip feeds for remote users.
        if follower.actor.is_remote:
            continue

        log.debug(
            "Distributing content_object=%s to actor=%s", content_object, follower.actor
        )
        FeedItem.objects.create(
            source=source,
            target=follower.actor,
            content_object=content_object,
            published_on=published_on,
        )

    if not source.is_remote:
        # Make sure it also shows up in the home feed.
        FeedItem.objects.create(
            source=source,
            target=source,
            content_object=content_object,
            published_on=published_on,
        )
