from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from activitypub.models.activity import Activity
from activitypub.models.actor import Actor
from activitypub.views import ActivityPubBaseView


class OutboxView(ActivityPubBaseView):
    """Returns the user's ActivityPub outbox."""

    def get(self, request, username):
        user = get_object_or_404(Actor, webfinger=f"{username}@{settings.SITE_URL}")
        activities = Activity.objects.filter(actor=user).order_by("-created_on")

        return JsonResponse(
            {
                "@context": "https://www.w3.org/ns/activitystreams",
                "type": "OrderedCollection",
                "totalItems": activities.count(),
                "items": [activity.to_activity_json() for activity in activities],
            },
            content_type="application/activity+json",
        )
