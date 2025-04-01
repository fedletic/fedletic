import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from activitypub.models.actor import Actor
from activitypub.views import ActivityPubBaseView

log = logging.getLogger(__name__)


class ActorView(ActivityPubBaseView):
    """Returns the ActivityPub actor profile for a user."""

    def get(self, request, username):
        webfinger = f"{username}@{settings.SITE_URL}"
        log.info("Looking up actor=%s", webfinger)

        actor = get_object_or_404(Actor, webfinger=webfinger)
        shared_inbox_path = reverse("shared-inbox")

        return JsonResponse(
            {
                "@context": [
                    "https://www.w3.org/ns/activitystreams",
                    "https://w3id.org/security/v1",
                    {
                        "toot": "https://joinmastodon.org/ns",
                        "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
                        "indexable": "toot:indexable",
                    },
                ],
                "id": actor.actor_url,
                "type": "Person",
                "preferredUsername": actor.webfinger.split("@")[0],
                "name": actor.name,
                "summary": actor.summary,
                "url": actor.profile_url,
                "inbox": actor.inbox_url,
                "outbox": actor.outbox_url,
                "followers": actor.followers_url,
                "following": actor.following_url,
                "published": actor.created_on,
                "publicKey": {
                    "id": actor.actor_url + "#main-key",
                    "owner": actor.actor_url,
                    "publicKeyPem": actor.public_key,
                },
                "endpoints": {
                    "sharedInbox": f"https://{settings.SITE_URL}{shared_inbox_path}"
                },
                "icon": {
                    "type": "Image",
                    "mediaType": actor.icon_mimetype,
                    "url": actor.icon_uri,
                },
                "image": {
                    "type": "Image",
                    "mediaType": actor.header_mimetype,
                    "url": actor.header_uri,
                },
                # Mastodon Specific.
                "indexable": False,
                "manuallyApprovesFollowers": False,  # TODO
            },
        )
