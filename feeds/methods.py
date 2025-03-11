import datetime

from activitypub.models import Actor

from .models import FeedItem


def distribute_to_feed(source: Actor, content_object):

    published_on = (
        content_object.workout.start_time
        if content_object.workout.start_time
        else datetime.datetime.now()
    )

    for target in source.followers.all():
        # Skip feeds for remote users.
        if target.target.is_remote:
            continue

        FeedItem.objects.create(
            source=source,
            target=target.target,
            content_object=content_object,
            published_on=published_on,
        )

    # Make sure it also shows up in the home feed.
    FeedItem.objects.create(
        source=source,
        target=source,
        content_object=content_object,
        published_on=published_on,
    )
