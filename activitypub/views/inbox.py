import json
import logging

from django.http import JsonResponse

from activitypub.models.activity import Activity
from activitypub.models.actor import Actor
from activitypub.tasks import process_activity
from activitypub.utils import webfinger_from_url
from activitypub.views import ActivityPubBaseView

log = logging.getLogger(__name__)


class InboxView(ActivityPubBaseView):
    # This handles both user and shared inboxes.
    def post(self, request, *args, **kwargs):
        activity_data = json.loads(request.body)
        username = webfinger_from_url(actor_url=activity_data.get("actor"))
        actor = Actor.objects.get(webfinger=username)

        if not actor:
            log.info("Incoming message for unknown actors=%s", username)
            return JsonResponse({"error": "Unknown actor"}, status=400)

        log.info(
            "Incoming activity=%s headers=%s", activity_data["id"], request.headers
        )
        activity = Activity.create_from_json(actor=actor, activity_data=activity_data)
        process_activity.process_activity.delay_on_commit(activity_id=activity.pk)
        return JsonResponse(
            {"message": "Activity received"},
            content_type="application/activity+json",
            status=202,
        )
