from django.core.management.base import BaseCommand

from workouts.methods import process_workout
from workouts.models import WorkoutAnchor


class Command(BaseCommand):
    help = "Description of what the import_fit command does"

    def add_arguments(self, parser):
        parser.add_argument("--anchor", required=True, help="Fit file location")

    def handle(self, anchor, *args, **options):
        anchor = WorkoutAnchor.objects.get(pk=anchor)
        process_workout(workout=anchor.get_workout())
