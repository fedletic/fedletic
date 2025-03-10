from activitypub.consts import ACTIVITY_TYPE_CREATE
from activitypub.models import Activity
from activitypub.tasks.publish_activity import publish_activity
from fedletic.celery import app
from feeds.methods import add_to_feed, distribute_to_feed
from workouts import methods as wo_methods
from workouts.consts import WORKOUT_STATUS_FINISHED, WORKOUT_STATUS_PROCESSING
from workouts.models import WorkoutAnchor


@app.task()
def process_workout(anchor_id):
    anchor = WorkoutAnchor.objects.get(id=anchor_id)

    anchor.workout.status = WORKOUT_STATUS_PROCESSING
    anchor.workout.save(update_fields=["status"])
    wo_methods.process_workout(workout=anchor.workout)

    # Refresh from DB to make sure any fields that got updated
    # in process workout are reflected downstream.
    anchor.workout.refresh_from_db()

    anchor.workout.status = WORKOUT_STATUS_FINISHED
    anchor.workout.save(update_fields=["status"])

    # Create the activity for sending the Note.
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

    # Save for the future.
    anchor.note_activities.add(note_activity)

    # And publish the Note activity, this goes out to non-local users only.
    for shared_inbox in anchor.actor.followers_shared_inboxes:
        publish_activity.apply(
            kwargs={
                "activity_id": note_activity.id,
                "inbox_url": shared_inbox,
            }
        )

    # TODO: Publish the workout activity.

    # Next up, we share it to local followers.
    for follower in anchor.actor.followers.filter(target__is_remote=False):
        distribute_to_feed(source=follower.actor, content_object=anchor)

    # And make sure it shows up in the feed of the creating actor, too.
    add_to_feed(source=anchor.actor, target=anchor.actor, content_object=anchor)
