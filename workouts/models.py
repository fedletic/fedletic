import dataclasses
import datetime
import pprint
from typing import Any, Dict, List

from django.db import models
from django.urls import reverse

from activitypub.utils import generate_ulid
from workouts.consts import (
    WORKOUT_ALPINE_SKIING,
    WORKOUT_CYCLING,
    WORKOUT_RUNNING,
    WORKOUT_STATUS_PENDING,
    WORKOUT_STATUSES_CHOICES,
    WORKOUT_TYPES_CHOICES,
)


@dataclasses.dataclass
class QuickViewAttribute:
    label: str
    value: str


class BaseWorkoutMixin(models.Model):
    """Base fields for all workouts."""

    name = models.CharField(max_length=255)
    summary = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=32, default=WORKOUT_STATUS_PENDING, choices=WORKOUT_STATUSES_CHOICES
    )
    fit_file = models.FileField(upload_to="fit-files", null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(
        null=True, blank=True, help_text="Duration in seconds"
    )

    class Meta:
        abstract = True

    @property
    def duration_display(self):
        seconds = self.duration if self.duration else 0
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60

        time_parts = []
        if hours > 0:
            time_parts.append(f"{hours}h")
        if minutes > 0 or hours > 0:
            time_parts.append(f"{minutes}m")
        time_parts.append(f"{seconds}s")

        return "".join(time_parts)


class ElevationMixin(models.Model):
    """Fields for workouts that involve elevation changes."""

    elevation_gain = models.FloatField(null=True, blank=True)
    elevation_loss = models.FloatField(null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def elevation_gain_display(self):
        gain = self.elevation_gain if self.elevation_gain is not None else 0
        return self._format_elevation(gain)

    @property
    def elevation_loss_display(self):
        loss = self.elevation_loss if self.elevation_loss is not None else 0
        return self._format_elevation(loss)

    def _format_elevation(self, elevation):
        """Format elevation values consistently."""
        if elevation >= 1000:
            return f"{elevation / 1000:.1f} km"
        else:
            return f"{int(elevation)} m"


class DistanceMixin(models.Model):
    """Fields for workouts that involve distance."""

    distance_in_meters = models.FloatField(null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def distance_in_meters_display(self):
        meters = self.distance_in_meters if self.distance_in_meters else 0

        if meters >= 1000:
            km = meters / 1000
            if km == int(km):
                return f"{int(km)}.0 km"
            elif km * 10 == int(km * 10):
                return f"{km:.1f} km"
            else:
                return f"{km:.2f} km"
        else:
            return f"{int(meters)} m"


class PhysiologicalMetricsMixin(models.Model):
    """Physiological metrics common to various workouts."""

    calories_burned = models.PositiveIntegerField(null=True, blank=True)
    heart_rate_min = models.IntegerField(null=True, blank=True)
    heart_rate_avg = models.IntegerField(null=True, blank=True)
    heart_rate_max = models.IntegerField(null=True, blank=True)
    time_in_hr_zones = models.JSONField(null=True, blank=True)

    # Training effect metrics
    training_effect_aerobic = models.FloatField(null=True, blank=True)
    training_effect_anaerobic = models.FloatField(null=True, blank=True)
    vo2_max = models.FloatField(null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def calories_burned_display(self):
        calories_burned = self.calories_burned if self.calories_burned else 0
        return f"{calories_burned} kcal"

    @property
    def time_in_hr_zones_display(self):
        """
        Format time spent in each heart rate zone.

        Returns formatted time for each zone:
        - Zone 1: 50-60% of max HR (Recovery)
        - Zone 2: 60-70% of max HR (Endurance)
        - Zone 3: 70-80% of max HR (Stamina)
        - Zone 4: 80-90% of max HR (Economy)
        - Zone 5: 90-100% of max HR (Speed)
        """
        if not self.time_in_hr_zones:
            return "No data"

        # Format each zone's time in minutes and seconds
        formatted_zones = []
        zone_names = ["Recovery", "Endurance", "Stamina", "Economy", "Speed"]

        for i, seconds in enumerate(self.time_in_hr_zones):
            if i >= len(zone_names):
                break

            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)

            if minutes > 0:
                time_str = f"{minutes}m {remaining_seconds}s"
            else:
                time_str = f"{remaining_seconds}s"

            # Format as zone name and time
            formatted_zones.append(f"Zone {i + 1} ({zone_names[i]}): {time_str}")

        return ", ".join(formatted_zones)


class EnvironmentalMetricsMixin(models.Model):
    """Environmental metrics for outdoor workouts."""

    altitude_min = models.FloatField(null=True, blank=True)
    altitude_max = models.FloatField(null=True, blank=True)
    altitude_avg = models.FloatField(null=True, blank=True)
    temperature_min = models.IntegerField(null=True, blank=True)
    temperature_max = models.IntegerField(null=True, blank=True)
    temperature_avg = models.IntegerField(null=True, blank=True)

    class Meta:
        abstract = True


class ActivityPubMixin(models.Model):
    """ActivityPub integration fields and methods."""

    ap_id = models.CharField(max_length=255, default=generate_ulid)
    ap_uri = models.URLField(max_length=1024, null=True, blank=True)
    local_uri = models.URLField(max_length=1024, null=True, blank=True)
    actor = models.ForeignKey(
        "activitypub.Actor",
        related_name="%(class)s_workouts",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    # A workout can have multiple activities, e.g for create, update, undo, et cetera.
    workout_activities = models.ManyToManyField(
        "activitypub.Activity", related_name="workout_activities"
    )
    # Same goes for the note.
    note_activities = models.ManyToManyField(
        "activitypub.Activity", related_name="note_activities"
    )

    class Meta:
        abstract = True

    @staticmethod
    def create_from_activitypub_object(ap_object: Dict[str, Any], actor) -> "Workout":
        """
        Create a Workout instance from an ActivityPub object.

        Parameters:
        ap_object (Dict[str, Any]): The ActivityPub object
        actor (Actor, optional): The Actor to associate with this workout

        Returns:
        Workout: A new Workout instance
        """
        # Extract the workout object if this is a Create activity
        if ap_object.get("type") == "Create" and "object" in ap_object:
            workout_object = ap_object["object"]
        else:
            workout_object = ap_object

        # Extract basic properties
        workout_type = workout_object.get("fedletic:workout_type")

        # Create a new workout instance
        workout = Workout(
            name=workout_object.get("name", "Imported Workout"),
            summary=workout_object.get("content"),
            workout_type=workout_type,
            ap_id=workout_object.get("id"),
            actor=actor,
        )

        # Handle published date as start_time
        if "published" in workout_object:
            try:
                workout.start_time = datetime.datetime.fromisoformat(
                    workout_object["published"]
                )
            except (ValueError, TypeError):
                pass

        # Process fedletic namespace properties
        for key, value in workout_object.items():
            if not key.startswith("fedletic:"):
                continue

            field_name = key.replace("fedletic:", "")

            # Skip if the field doesn't exist on the model
            if not hasattr(workout, field_name):
                continue

            # Get the field type to handle conversions
            field = workout._meta.get_field(field_name)

            # Handle different field types
            if isinstance(field, models.DateTimeField) and value:
                try:
                    setattr(workout, field_name, datetime.datetime.fromisoformat(value))
                except (ValueError, TypeError):
                    continue
            elif isinstance(field, (models.FloatField, models.IntegerField)) and value:
                try:
                    if isinstance(field, models.IntegerField):
                        value = int(value)
                    else:
                        value = float(value)
                    setattr(workout, field_name, value)
                except (ValueError, TypeError):
                    continue
            else:
                setattr(workout, field_name, value)

        # Set federation URIs
        workout.ap_uri = workout_object.get("id")
        local_path = reverse(
            "frontend-workout",
            kwargs={"webfinger": actor.webfinger, "workout_id": workout.ap_id},
        )
        workout.local_uri = local_path

        # Save the workout
        workout.save()

        return workout

    @property
    def note_uri(self):
        """Get the URI for notes associated with this workout."""
        if not self.local_uri:
            return None
        return f"{self.local_uri}/note"

    def set_activity_pub_uris(self, actor=None, ap_uri=None, local_uri=None):
        """Set ActivityPub URIs for this workout."""
        if actor:
            self.actor = actor

        if not ap_uri:
            ap_uri = f"https://your-domain.com/workouts/{self.id}"
        self.ap_uri = ap_uri

        if not local_uri:
            local_uri = f"/workouts/{self.id}"
        self.local_uri = local_uri

        self.save()

    def as_activitypub_object(self) -> Dict[str, Any]:
        """Serialize the workout to an ActivityPub object format."""
        if not self.actor:
            raise ValueError("Workout must have an actor to be serialized")

        # Basic workout object
        workout_object = {
            "id": self.ap_id,
            "type": "Workout",
            "name": self.name,
            "published": (
                self.start_time.isoformat()
                if self.start_time
                else datetime.datetime.now().isoformat()
            ),
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"fedletic": "https://fedletic.com/ns#"},
            ],
            "attributedTo": self.actor.actor_url,
            "url": self.ap_uri,
            "fedletic:workout_type": self.workout_type,
        }

        if self.summary:
            workout_object["content"] = self.summary

        if self.duration:
            workout_object["fedletic:duration"] = self.duration

        workout_attributes = self._get_serializable_attributes()
        workout_object.update(workout_attributes)

        # Create the full ActivityPub activity
        return workout_object

    def _get_serializable_attributes(self) -> Dict[str, Any]:
        """Extract serializable attributes from the workout model."""
        # Fields to exclude
        excluded_fields = [
            "id",
            "name",
            "summary",
            "fit_file",
            "status",
            "_state",
            "workout_type",
            "actor",
            "ap_id",
            "ap_uri",
            "local_uri",
            "workout_activities",
            "note_activities",
            "images",  # TODO: handle this.
            "comments",  # TODO: handle this.
        ]

        serialized = {}

        # Collect field values
        for field in self._meta.get_fields():
            # Skip excluded fields and relationships
            if (
                field.name in excluded_fields
                or isinstance(field, models.ForeignKey)
                or isinstance(field, models.ManyToManyField)
            ):
                continue

            try:
                value = getattr(self, field.name)
                if value is None:
                    continue

                # Format DateTimeField values
                if isinstance(field, models.DateTimeField) and value:
                    value = value.isoformat()

                # Use fedletic namespace
                serialized[f"fedletic:{field.name}"] = value
            except AttributeError:
                continue

        pprint.pprint(serialized)
        return serialized


class RunWorkoutMixin(models.Model):
    """Running-specific fields and methods."""

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

    class Meta:
        abstract = True

    @property
    def pace_display(self):
        """Format pace in seconds per kilometer to min:sec format."""
        if not self.pace_avg:
            return "N/A"

        minutes = self.pace_avg // 60
        seconds = self.pace_avg % 60
        return f"{minutes}:{seconds:02d}/km"


class SwimWorkoutMixin(models.Model):
    """Swimming-specific fields and methods."""

    pace_avg = models.IntegerField(
        help_text="Average pace in seconds per 100m", null=True, blank=True
    )
    pace_best = models.IntegerField(
        help_text="Best pace in seconds per 100m", null=True, blank=True
    )
    pool_length = models.IntegerField(
        help_text="Pool length in meters", null=True, blank=True
    )
    is_open_water = models.BooleanField(default=False)
    stroke_count = models.IntegerField(
        help_text="Total number of strokes", null=True, blank=True
    )
    strokes_per_length_avg = models.FloatField(null=True, blank=True)
    swolf_avg = models.IntegerField(
        help_text="Average swim golf score (strokes + seconds)", null=True, blank=True
    )
    swolf_best = models.IntegerField(
        help_text="Best swim golf score", null=True, blank=True
    )
    freestyle_time = models.IntegerField(null=True, blank=True)
    backstroke_time = models.IntegerField(null=True, blank=True)
    breaststroke_time = models.IntegerField(null=True, blank=True)
    butterfly_time = models.IntegerField(null=True, blank=True)
    drill_time = models.IntegerField(null=True, blank=True)
    mixed_time = models.IntegerField(null=True, blank=True)
    rest_time = models.IntegerField(
        help_text="Total rest time in seconds", null=True, blank=True
    )
    stroke_rate_avg = models.FloatField(
        help_text="Average strokes per minute", null=True, blank=True
    )

    class Meta:
        abstract = True


class CyclingWorkoutMixin(models.Model):
    """Cycling-specific fields and methods."""

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

    class Meta:
        abstract = True

    @property
    def speed_display(self):
        """Format speed in m/s to km/h."""
        if not self.speed_avg:
            return "N/A"

        # Convert m/s to km/h
        kmh = self.speed_avg * 3.6
        return f"{kmh:.1f} km/h"


class Workout(
    BaseWorkoutMixin,
    DistanceMixin,
    ElevationMixin,
    PhysiologicalMetricsMixin,
    EnvironmentalMetricsMixin,
    ActivityPubMixin,
    RunWorkoutMixin,
    SwimWorkoutMixin,
    CyclingWorkoutMixin,
    models.Model,
):
    """
    Unified workout model that includes fields from all workout types.
    """

    workout_type = models.CharField(
        max_length=50, choices=WORKOUT_TYPES_CHOICES, db_index=True
    )

    class Meta:
        ordering = ("start_time", "id")

    def get_absolute_url(self):
        """Generate a URL to view this workout."""
        return reverse("workout_detail", kwargs={"pk": self.pk})

    @property
    def quick_view_attrs(self) -> List[QuickViewAttribute]:
        """Get quick view attributes based on workout type."""
        attrs = [
            QuickViewAttribute(
                label="Duration",
                value=self.duration_display,
            ),
            QuickViewAttribute(
                label="Calories",
                value=self.calories_burned_display,
            ),
        ]
        # Add type-specific attributes
        if self.workout_type in [
            WORKOUT_RUNNING,
            WORKOUT_CYCLING,
            WORKOUT_ALPINE_SKIING,
        ]:
            attrs.append(
                QuickViewAttribute(
                    label="Distance",
                    value=self.distance_in_meters_display,
                )
            )

        return attrs

    @property
    def workout_attributes(self):
        """
        Return all relevant workout attributes in a structured format.

        Returns:
            List[Dict]: A list of dictionaries with keys:
                - key: Field name
                - label: Human-readable label
                - value: Raw value
                - display_value: Formatted value for display
        """
        attributes = []

        # Map of field names to human-readable labels
        field_labels = {
            # Base workout fields
            "duration": "Duration",
            # Distance fields"
            "distance_in_meters": "Distance",
            # Physiological metrics
            "calories_burned": "Calories Burned",
            "heart_rate_min": "Min Heart Rate",
            "heart_rate_avg": "Average Heart Rate",
            "heart_rate_max": "Max Heart Rate",
            "training_effect_aerobic": "Aerobic Training Effect",
            "training_effect_anaerobic": "Anaerobic Training Effect",
            "vo2_max": "VO2 Max",
            # Environmental metrics
            "altitude_min": "Min Altitude",
            "altitude_max": "Max Altitude",
            "altitude_avg": "Average Altitude",
            "temperature_min": "Min Temperature",
            "temperature_max": "Max Temperature",
            "temperature_avg": "Average Temperature",
            # Running fields
            "pace_avg": "Average Pace",
            "pace_best": "Best Pace",
            "cadence_avg": "Average Cadence",
            "cadence_max": "Maximum Cadence",
            "stride_length_avg": "Average Stride Length",
            "vertical_oscillation_avg": "Average Vertical Oscillation",
            "ground_contact_time_avg": "Average Ground Contact Time",
            "elevation_gain": "Elevation Gain",
            "elevation_loss": "Elevation Loss",
            # Swimming fields
            "pool_length": "Pool Length",
            "is_open_water": "Open Water",
            "stroke_count": "Stroke Count",
            "strokes_per_length_avg": "Average Strokes per Length",
            "swolf_avg": "Average SWOLF",
            "swolf_best": "Best SWOLF",
            "freestyle_time": "Freestyle Time",
            "backstroke_time": "Backstroke Time",
            "breaststroke_time": "Breaststroke Time",
            "butterfly_time": "Butterfly Time",
            "drill_time": "Drill Time",
            "mixed_time": "Mixed Time",
            "rest_time": "Rest Time",
            "stroke_rate_avg": "Average Stroke Rate",
            # Cycling fields
            "speed_avg": "Average Speed",
            "speed_max": "Max Speed",
            "power_avg": "Average Power",
            "power_max": "Max Power",
            "grade_avg": "Average Grade",
            "grade_max": "Maximum Grade",
            "grade_min": "Minimum Grade",
        }

        # Fields with custom display properties
        display_properties = {
            "duration": "duration_display",
            "distance_in_meters": "distance_in_meters_display",
            "calories_burned": "calories_burned_display",
            "pace_avg": "pace_display",
            "speed_avg": "speed_display",
            "elevation_gain": "elevation_gain_display",
            "elevation_loss": "elevation_loss_display",
            "time_in_hr_zones": "time_in_hr_zones_display",
            "workout_type": "get_workout_type_display",
        }

        # Get all fields from the model
        for field in self._meta.get_fields():
            # Skip many-to-many relationships, foreign keys, and some internal fields
            if field.name.startswith("_") or field.name in [
                "workout_activities",
                "note_activities",
                "images",
                "comments",
                "actor",
                "ap_id",
                "ap_uri",
                "local_uri",
                "fit_file",
                "id",
                "status",
                "name",
                "summary",
                "created_on",
                "updated_on",
            ]:
                continue

            # Skip if it's a relationship field
            if field.is_relation:
                continue

            # Get the raw value
            value = getattr(self, field.name, None)

            # Skip if the value is None
            if value is None:
                continue

            # Get the display value
            display_value = None
            if field.name in display_properties:
                display_property = display_properties[field.name]
                display_value = getattr(self, display_property, str(value))
            else:
                # Format datetime fields
                if isinstance(value, datetime.datetime):
                    display_value = value.strftime("%Y-%m-%d %H:%M:%S")
                # Format boolean fields
                elif isinstance(value, bool):
                    display_value = "Yes" if value else "No"
                # Format float fields
                elif isinstance(value, float):
                    display_value = f"{value:.2f}"
                else:
                    display_value = str(value)

            # Get the label
            label = field_labels.get(field.name, field.name.replace("_", " ").title())

            attributes.append(
                {
                    "key": field.name,
                    "label": label,
                    "value": value,
                    "display_value": display_value,
                }
            )

        # Sort by labels
        return sorted(attributes, key=lambda x: x["label"])


class Comment(models.Model):
    """
    TODO: Load comments from inbox.
    """

    ap_id = models.CharField(max_length=255, default=generate_ulid)
    ap_uri = models.URLField(max_length=1024, null=True, blank=True)
    local_uri = models.URLField(max_length=1024, null=True, blank=True)
    actor = models.ForeignKey(
        "activitypub.Actor",
        related_name="comments",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    content = models.TextField()
    workout = models.ForeignKey(
        "workouts.Workout", related_name="comments", on_delete=models.CASCADE
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    response_to = models.ForeignKey(
        "workouts.Comment", on_delete=models.CASCADE, null=True, blank=True
    )


class ImageAttachment(models.Model):
    id = models.CharField(primary_key=True, default=generate_ulid, editable=False)
    workout = models.ForeignKey(
        "workouts.Workout", related_name="images", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="workout-images")
    blurhash = models.TextField()
    image_dimensions = models.JSONField()
    file_size = models.IntegerField()
    file_name = models.CharField()
