import logging

from activitypub.events import events
from activitypub.models import Activity
from feeds.methods import distribute_to_feed
from workouts.models import Workout

log = logging.getLogger(__name__)


@events.on("activity")
def process_workout(activity_id):
    activity = Activity.objects.get(pk=activity_id)

    if not activity.activity_type == "Create":
        # TODO: support update etcetera.
        return

    if not activity.object_json:
        # Not going to do anything with this, as we expect an object to be inside of the Create.
        # TODO: support URIs
        return

    if not activity.object_json["type"] == "Workout":
        # Not a workout, so not applicable here.
        return

    log.info("Creating incoming workout=%s", activity.object_json)

    workout = Workout.create_from_activitypub_object(
        ap_object=activity.object_json, actor=activity.actor
    )
    distribute_to_feed(source=workout.actor, content_object=workout)
