from activitypub.consts import ACTIVITY_TYPE_CREATE
from activitypub.models import Activity
from activitypub.tasks.publish_activity import publish_activity
from fedletic.celery import app
from feeds.methods import distribute_to_feed
from workouts import methods as wo_methods
from workouts.consts import WORKOUT_STATUS_FINISHED, WORKOUT_STATUS_PROCESSING
from workouts.models import Workout


@app.task()
def process_workout(workout_id):
    workout = Workout.objects.get(id=workout_id)

    workout.status = WORKOUT_STATUS_PROCESSING
    workout.save(update_fields=["status"])
    wo_methods.process_workout(workout=workout)

    # Refresh from DB to make sure any fields that got updated
    # in process workout are reflected downstream.
    workout.refresh_from_db()

    workout.status = WORKOUT_STATUS_FINISHED
    workout.save(update_fields=["status"])

    # Create the activity for sending the Note.
    note_activity = Activity.create_from_kwargs(
        actor=workout.actor,
        target=None,
        context="https://www.w3.org/ns/activitystreams",
        activity_type=ACTIVITY_TYPE_CREATE,
        activity_object={
            "id": workout.note_uri,
            "type": "Note",
            "content": workout.summary,
            "attributedTo": workout.actor.profile_url,
            "published": workout.start_time.isoformat(),
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "cc": [workout.actor.followers_url],
        },
        to=["https://www.w3.org/ns/activitystreams#Public"],
        cc=[workout.actor.followers_url],
        published=workout.start_time.isoformat(),
    )

    # Save for the future, I guess.
    workout.note_activities.add(note_activity)

    # Now the workout activity!
    workout_activity = Activity.create_from_kwargs(
        actor=workout.actor,
        target=None,
        context="https://www.w3.org/ns/activitystreams",
        activity_type=ACTIVITY_TYPE_CREATE,
        activity_object={
            "id": workout.ap_uri,
            "type": "Workout",
            "content": workout.ap_uri,
            "attributedTo": workout.actor.profile_url,
            "published": workout.start_time.isoformat(),
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "cc": [workout.actor.followers_url],
        },
        to=["https://www.w3.org/ns/activitystreams#Public"],
        cc=[workout.actor.followers_url],
        published=workout.start_time.isoformat(),
    )

    # And publish the Note & Workout activity,
    # this goes out to non-local users only.
    for shared_inbox in workout.actor.followers_shared_inboxes:
        publish_activity.apply(
            kwargs={
                "activity_id": note_activity.id,
                "inbox_url": shared_inbox,
            }
        )
        publish_activity.apply(
            kwargs={
                "activity_id": workout_activity.id,
                "inbox_url": shared_inbox,
            }
        )

    # TODO: Publish the workout activity.
    # Next up, we share it to local followers + own user.
    distribute_to_feed(source=workout.actor, content_object=workout)
