import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from workouts.models import Workout

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recount all likes and comments on all workouts"

    @atomic
    def check_workout(self, workout):
        self.stdout.write(f"recounting likes and comments for workout {workout.pk}")
        workout.like_count = workout.likes.count()
        workout.comment_count = workout.comments.count()
        workout.save()

    def handle(self, *args, **options):
        # Command implementation goes here
        self.stdout.write("Recounting all likes and comments for all workouts.")

        for workout in Workout.objects.all():
            self.check_workout(workout)

        # Example success message:
        self.stdout.write(
            self.style.SUCCESS("Recounted all likes and comments for all workouts.")
        )
