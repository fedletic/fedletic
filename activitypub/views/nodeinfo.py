from django.conf import settings
from django.http import JsonResponse

from activitypub.models import Actor
from activitypub.views import ActivityPubBaseView


class NodeInfoView(ActivityPubBaseView):
    """Returns the ActivityPub actor profile for a user."""

    def get(self, request):

        return JsonResponse(
            {
                "version": "2.0",
                "software": {"name": "fedletic", "version": settings.VERSION},
                "protocols": ["activitypub"],
                "services": {"inbound": [], "outbound": []},
                "openRegistrations": True,
                "usage": {
                    "users": {"total": Actor.objects.filter(is_remote=False).count()}
                },
                "metadata": {},
            }
        )
