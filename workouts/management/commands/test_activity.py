from django.core.management.base import BaseCommand

from activitypub.consts import ACTIVITY_TYPE_CREATE
from activitypub.models import Activity
from activitypub.tasks.publish_activity import publish_activity
from workouts.models import WorkoutAnchor


class Command(BaseCommand):
    help = "Description of what the import_fit command does"

    def handle(self, *args, **options):
        anchor = WorkoutAnchor.objects.get(ap_id="01jnnjc5qmvf1xq40rfn6trbhc")
        note_activity = Activity.create_from_kwargs(
            actor=anchor.actor,
            target=None,
            context="https://www.w3.org/ns/activitystreams",
            activity_type=ACTIVITY_TYPE_CREATE,
            activity_object={
                "id": anchor.note_uri,
                "type": "Note",
                "content": anchor.workout.summary,
                "attributedTo": anchor.actor.profile_url,
                "published": anchor.workout.start_time.isoformat(),
                "to": ["https://www.w3.org/ns/activitystreams#Public"],
                "cc": [anchor.actor.followers_url],
            },
            to=["https://www.w3.org/ns/activitystreams#Public"],
            cc=[anchor.actor.followers_url],
            published=anchor.workout.start_time.isoformat(),
        )
        publish_activity.apply(
            kwargs={
                "activity_id": note_activity.id,
                "inbox_url": "https://famichiki.jp/inbox",
            }
        )
