from urllib.parse import unquote

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from activitypub.models.actor import Actor
from activitypub.views import ActivityPubBaseView


class WellKnownNodeInfoView(ActivityPubBaseView):
    CONTENT_TYPE = "application/jrd+json"

    def get(self, request):
        path = reverse("nodeinfo")
        return JsonResponse(
            {
                "links": [
                    {
                        "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                        "href": f"https://{settings.SITE_URL}{path}",
                    }
                ]
            }
        )


class WellKnownWebFingerView(ActivityPubBaseView):
    CONTENT_TYPE = "application/jrd+json"

    def get(self, request):
        resource = request.GET.get("resource", "")

        # Ensure it's a properly formatted WebFinger request
        if not resource.startswith("acct:"):
            return JsonResponse({"error": "Invalid WebFinger request"}, status=400)

        # Extract the username from the resource (e.g., "acct:john@fedletic.example")
        resource = unquote(resource)
        username = resource.replace("acct:", "")
        actor = get_object_or_404(Actor, webfinger=username)

        return JsonResponse(
            {
                "subject": f"acct:{actor.webfinger}",
                "aliases": [actor.actor_url],
                "links": [
                    {
                        "rel": "self",
                        "type": "application/activity+json",
                        "href": actor.actor_url,
                    }
                ],
            }
        )
