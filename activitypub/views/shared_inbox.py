import json

from django.db import IntegrityError
from django.http import JsonResponse

from activitypub.models.activity import Activity
from activitypub.views import ActivityPubBaseView


class SharedInboxView(ActivityPubBaseView):
    """Handles incoming ActivityPub messages."""

    def post(self, request):
        data = json.loads(request.body)
        ap_id = data["id"]
        try:
            Activity.objects.create(
                id=ap_id, activity_type=data["type"], object_json=data
            )
        except IntegrityError:
            # No one is perfect so there's a chance a server might talk to us twice.
            pass

        return JsonResponse(
            {"message": "Activity received"},
            status=202,
            content_type="application/activity+json",
        )
