from activitypub.models import Actor

from .models import FeedItem


def add_to_feed(source: Actor, target: Actor, content_object):
    # Skip feeds for remote users.
    if target.is_remote:
        return

    FeedItem.objects.create(source=source, target=target, content_object=content_object)


def distribute_to_feed(source: Actor, content_object):
    for target in source.followers.all():
        # Skip feeds for remote users.
        if target.target.is_remote:
            continue

        FeedItem.objects.create(
            source=source, target=target, content_object=content_object
        )
