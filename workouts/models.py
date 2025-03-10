import datetime
from typing import Any, Dict

from django.db import models

from activitypub.utils import generate_ulid
from workouts.consts import WORKOUT_STATUS_PENDING, WORKOUT_STATUSES_CHOICES


class WorkoutAnchor(models.Model):
    ap_id = models.CharField(default=generate_ulid)
    # The AP uri on either our local, or remote server.
    ap_uri = models.URLField(max_length=1024)
    # The AP uri on our local server
    local_uri = models.URLField(max_length=1024)
    workout_activities = models.ManyToManyField(
        "activitypub.Activity", related_name="workout_activities"
    )
    note_activities = models.ManyToManyField(
        "activitypub.Activity", related_name="note_activities"
    )
    actor = models.ForeignKey(
        "activitypub.Actor", related_name="workout_anchors", on_delete=models.CASCADE
    )

    @property
    def workout(self):
        if hasattr(self, "runworkout_workout"):
            return self.runworkout_workout
        if hasattr(self, "cyclingworkout_workout"):
            return self.cyclingworkout_workout
        if hasattr(self, "swimworkout_workout"):
            return self.swimworkout_workout

    @property
    def note_uri(self):
        return f"{self.local_uri}/note"

    def get_workout_type(self) -> str:
        """Return the type of workout as a string."""
        if hasattr(self, "runworkout_workout"):
            return "RunWorkout"
        if hasattr(self, "cyclingworkout_workout"):
            return "CyclingWorkout"
        if hasattr(self, "swimworkout_workout"):
            return "SwimWorkout"
        return "Workout"

    def as_activitypub_object(self) -> Dict[str, Any]:
        """
        Serialize the workout to an ActivityPub object format.

        Returns:
            Dict[str, Any]: The workout serialized as an ActivityPub object
        """
        workout = self.workout
        if not workout:
            # Return a minimal object if no workout is associated
            return {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": self.ap_id,
                "type": "Workout",
                "actor": self.actor.profile_url,
                "published": datetime.datetime.now().isoformat(),
            }

        # Basic workout object that will be the "object" of the activity
        workout_object = {
            "id": self.ap_id,
            "type": self.get_workout_type(),
            "name": workout.name,
            "published": (
                workout.start_time.isoformat()
                if workout.start_time
                else datetime.datetime.now().isoformat()
            ),
        }

        # Add description if available
        if workout.description:
            workout_object["content"] = workout.description

        # Add duration
        if workout.duration:
            workout_object["fedletic:duration"] = workout.duration

        # Add workout-specific attributes based on type
        workout_attributes = self._get_serializable_attributes(workout)
        workout_object.update(workout_attributes)

        # Create the full ActivityPub activity with the workout as its object
        return {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"fedletic": "https://fedletic.com/ns#"},
            ],
            "id": f"{self.ap_id}/activity",
            "type": "Create",
            "actor": self.actor.ap_id,
            "object": workout_object,
        }

    def _get_serializable_attributes(self, workout) -> Dict[str, Any]:
        """
        Extract serializable attributes from the workout model.
        Excludes certain Django model fields and formats others for ActivityPub.

        Args:
            workout: The workout model instance

        Returns:
            Dict[str, Any]: Dictionary of serializable workout attributes
        """
        # Fields to exclude from serialization
        excluded_fields = [
            "id",
            "name",
            "anchor",
            "description",
            "fit_file",
            "status",
            "_state",
            "_anchor_cache",
            "_prefetched_objects_cache",
        ]

        # Get all fields from the model
        workout_type = type(workout)
        serialized = {}

        # First collect all field values
        for field in workout_type._meta.get_fields():
            # Skip excluded fields and relationships
            if field.name in excluded_fields or isinstance(field, models.ForeignKey):
                continue

            try:
                value = getattr(workout, field.name)
                # Skip empty values
                if value is None:
                    continue

                # Format DateTimeField values
                if isinstance(field, models.DateTimeField) and value:
                    value = value.isoformat()

                # Format JSONField values
                if isinstance(field, models.JSONField) and value:
                    # Already a dict, no need to convert
                    pass

                # Use the fedletic namespace for domain-specific fields
                serialized[f"fedletic:{field.name}"] = value
            except AttributeError:
                # Skip attributes that don't exist
                continue

        # Add specialized data based on workout type
        if hasattr(workout, "distance_in_meters") and workout.distance_in_meters:
            serialized["fedletic:distance"] = {
                "type": "Distance",
                "fedletic:meters": workout.distance_in_meters,
            }

        return serialized


class Workout(models.Model):
    name = models.CharField(max_length=255)
    anchor = models.OneToOneField(
        WorkoutAnchor,
        on_delete=models.CASCADE,
        related_name="%(class)s_workout",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=32, default=WORKOUT_STATUS_PENDING, choices=WORKOUT_STATUSES_CHOICES
    )
    fit_file = models.FileField(upload_to="fit-files", null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    start_time = models.DateTimeField(
        null=True, blank=True
    )  # Start timestamp is crucial
    end_time = models.DateTimeField(null=True, blank=True)  # End timestamp
    duration = models.PositiveIntegerField(
        null=True, blank=True, help_text="Duration in seconds"
    )
    calories_burned = models.PositiveIntegerField(null=True, blank=True)
    heart_rate_min = models.IntegerField(null=True, blank=True)
    heart_rate_avg = models.IntegerField(null=True, blank=True)
    heart_rate_max = models.IntegerField(null=True, blank=True)
    time_in_hr_zones = models.JSONField(null=True, blank=True)

    altitude_min = models.FloatField(
        null=True, blank=True
    )  # Minimum altitude in meters
    altitude_max = models.FloatField(
        null=True, blank=True
    )  # Maximum altitude in meters
    altitude_avg = models.FloatField(
        null=True, blank=True
    )  # Average altitude in meters
    temperature_min = models.IntegerField(
        null=True, blank=True
    )  # Min temperature in Celsius
    temperature_max = models.IntegerField(
        null=True, blank=True
    )  # Max temperature in Celsius
    temperature_avg = models.IntegerField(
        null=True, blank=True
    )  # Average temperature in Celsius

    class Meta:
        abstract = True


class RunWorkout(Workout):

    distance_in_meters = models.FloatField(null=True, blank=True)
    pace_avg = models.IntegerField(
        help_text="Average pace in seconds per kilometer", null=True, blank=True
    )
    pace_best = models.IntegerField(
        help_text="Best pace in seconds per kilometer", null=True, blank=True
    )
    cadence_avg = models.IntegerField(
        help_text="Average steps per minute", null=True, blank=True
    )
    cadence_max = models.IntegerField(
        help_text="Maximum steps per minute", null=True, blank=True
    )
    stride_length_avg = models.FloatField(
        help_text="Average stride length in meters", null=True, blank=True
    )
    vertical_oscillation_avg = models.FloatField(
        help_text="Average vertical oscillation in cm", null=True, blank=True
    )
    ground_contact_time_avg = models.IntegerField(
        help_text="Average ground contact time in ms", null=True, blank=True
    )
    training_effect_aerobic = models.FloatField(
        null=True, blank=True
    )  # Aerobic training effect (0.0-5.0)
    training_effect_anaerobic = models.FloatField(
        null=True, blank=True
    )  # Anaerobic training effect (0.0-5.0)
    vo2_max = models.FloatField(null=True, blank=True)  # Estimated VO2 Max
    elevation_gain = models.FloatField(null=True, blank=True)
    elevation_loss = models.FloatField(null=True, blank=True)


class SwimWorkout(Workout):
    distance_in_meters = models.FloatField(null=True, blank=True)
    pace_avg = models.IntegerField(
        help_text="Average pace in seconds per 100m", null=True, blank=True
    )
    pace_best = models.IntegerField(
        help_text="Best pace in seconds per 100m", null=True, blank=True
    )

    # Pool-specific metrics
    pool_length = models.IntegerField(
        help_text="Pool length in meters", null=True, blank=True
    )
    is_open_water = models.BooleanField(default=False)

    # Stroke metrics
    stroke_count = models.IntegerField(
        help_text="Total number of strokes", null=True, blank=True
    )
    strokes_per_length_avg = models.FloatField(null=True, blank=True)

    # Efficiency metrics
    swolf_avg = models.IntegerField(
        help_text="Average swim golf score (strokes + seconds)", null=True, blank=True
    )
    swolf_best = models.IntegerField(
        help_text="Best swim golf score", null=True, blank=True
    )

    # Stroke types - storing time spent in each stroke type (in seconds)
    freestyle_time = models.IntegerField(null=True, blank=True)
    backstroke_time = models.IntegerField(null=True, blank=True)
    breaststroke_time = models.IntegerField(null=True, blank=True)
    butterfly_time = models.IntegerField(null=True, blank=True)
    drill_time = models.IntegerField(null=True, blank=True)
    mixed_time = models.IntegerField(null=True, blank=True)

    # Rest metrics
    rest_time = models.IntegerField(
        help_text="Total rest time in seconds", null=True, blank=True
    )

    # Specialized metrics
    stroke_rate_avg = models.FloatField(
        help_text="Average strokes per minute", null=True, blank=True
    )
    training_effect_aerobic = models.FloatField(
        null=True, blank=True
    )  # Aerobic training effect (0.0-5.0)


class CyclingWorkout(Workout):
    distance_in_meters = models.FloatField(null=True, blank=True)
    speed_avg = models.FloatField(
        help_text="Average speed in m/s", null=True, blank=True
    )
    speed_max = models.FloatField(
        help_text="Maximum speed in m/s", null=True, blank=True
    )
    power_avg = models.IntegerField(
        help_text="Average power in watts", null=True, blank=True
    )
    power_max = models.IntegerField(
        help_text="Maximum power in watts", null=True, blank=True
    )
    cadence_avg = models.IntegerField(
        help_text="Average pedal cadence in rpm", null=True, blank=True
    )
    cadence_max = models.IntegerField(
        help_text="Maximum pedal cadence in rpm", null=True, blank=True
    )
    grade_avg = models.FloatField(
        help_text="Average grade in percent", null=True, blank=True
    )
    grade_max = models.FloatField(
        help_text="Maximum positive grade in percent", null=True, blank=True
    )
    grade_min = models.FloatField(
        help_text="Maximum negative grade in percent", null=True, blank=True
    )
    elevation_gain = models.FloatField(null=True, blank=True)
    elevation_loss = models.FloatField(null=True, blank=True)
