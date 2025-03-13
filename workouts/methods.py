import datetime
import logging

from django.conf import settings
from django.db.transaction import atomic
from django.urls import reverse
from garmin_fit_sdk import Decoder, Stream

from workouts.consts import WORKOUT_TYPES_LIST
from workouts.exceptions import FitFileException
from workouts.models import Workout

log = logging.getLogger(__name__)


def generate_cycling_workout_description(workout):
    parts = []

    # Distance
    if workout.distance_in_meters:
        distance_km = workout.distance_in_meters / 1000
        if distance_km < 10:
            distance_text = f"quick {distance_km:.1f} km"
        elif distance_km < 30:
            distance_text = f"{distance_km:.1f} km"
        elif distance_km < 70:
            distance_text = f"solid {distance_km:.1f} km"
        else:
            distance_text = f"long {distance_km:.1f} km"
        parts.append(f"Just finished a {distance_text} ride")
    else:
        parts.append("Just wrapped up a ride")

    # Duration
    if workout.duration:
        hours = workout.duration // 3600
        minutes = (workout.duration % 3600) // 60

        if hours > 0:
            time_text = f"{hours} hour{'s' if hours > 1 else ''}"
            if minutes > 0:
                time_text += f" and {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            time_text = f"{minutes} minute{'s' if minutes > 1 else ''}"

        parts[0] += f" in {time_text}"

    # Average Speed
    if workout.speed_avg:
        speed_kph = workout.speed_avg * 3.6  # Convert m/s to km/h
        parts.append(f"Averaged {speed_kph:.1f} km/h")

    # Max Speed
    if workout.speed_max:
        max_speed_kph = workout.speed_max * 3.6  # Convert m/s to km/h
        parts.append(f"Hit a top speed of {max_speed_kph:.1f} km/h")

    # Heart Rate
    hr_parts = []
    if workout.heart_rate_avg:
        hr_parts.append(f"avg HR of {workout.heart_rate_avg} bpm")
    if workout.heart_rate_max:
        hr_parts.append(f"max HR of {workout.heart_rate_max} bpm")

    if hr_parts:
        parts.append(f"Pushed myself to an {' and '.join(hr_parts)}")

    # Power metrics
    if workout.power_avg:
        parts.append(f"Put out {workout.power_avg} watts on average")

    # Cadence
    if workout.cadence_avg:
        parts.append(f"Kept my cadence at {workout.cadence_avg} rpm")

    # Elevation
    if workout.elevation_gain and workout.elevation_gain > 100:
        parts.append(f"Climbed {workout.elevation_gain:.0f}m of elevation")

    # Calories
    if workout.calories_burned:
        parts.append(f"Burned {workout.calories_burned} calories")

    # Create final description
    description = ". ".join(parts)

    # Add a personal feeling statement based on available metrics
    if workout.distance_in_meters and workout.duration:
        time_hours = workout.duration / 3600
        distance_km = workout.distance_in_meters / 1000

        if distance_km / time_hours > 25:
            description += ". Feeling fast today! 🚴‍♂️💨"
        elif workout.elevation_gain and workout.elevation_gain > 500:
            description += ". My legs are definitely feeling those climbs! 🏔️"
        elif workout.duration > 7200:  # More than 2 hours
            description += ". A bit tired but satisfied with the long ride today! 💪"
        else:
            description += ". Good to be out on the bike! 🚴‍♂️"
    else:
        description += ". Another ride in the books! 🚴‍♂️"

    return description


def update_cycling_workout(workout, workout_data, session):
    # Naming convention based on date and time
    start_time = session.get("start_time")
    if start_time:
        date_str = start_time.strftime("%Y-%m-%d")
        workout_data["name"] = f"Cycling - {date_str}"
        workout_data["start_time"] = start_time

    # Duration and distance
    workout_data["duration"] = session.get("total_elapsed_time", 0)
    workout_data["distance_in_meters"] = session.get("total_distance", 0)

    # Timestamps
    workout_data["end_time"] = session.get("timestamp")

    # Heart rate data
    workout_data["heart_rate_avg"] = session.get("avg_heart_rate")
    workout_data["heart_rate_max"] = session.get("max_heart_rate")
    workout_data["heart_rate_min"] = session.get("min_heart_rate")

    # Calories
    workout_data["calories_burned"] = session.get("total_calories")

    # Power data
    workout_data["power_avg"] = session.get("avg_power")
    workout_data["power_max"] = session.get("max_power")

    # Time in zones
    if "time_in_hr_zone" in session:
        workout_data["time_in_hr_zones"] = session["time_in_hr_zone"]

    # Speed metrics
    if "enhanced_avg_speed" in session:
        workout_data["speed_avg"] = session["enhanced_avg_speed"]
    else:
        workout_data["speed_avg"] = session.get("avg_speed")

    if "enhanced_max_speed" in session:
        workout_data["speed_max"] = session["enhanced_max_speed"]
    else:
        workout_data["speed_max"] = session.get("max_speed")

    # Cadence
    workout_data["cadence_avg"] = session.get("avg_cadence")
    workout_data["cadence_max"] = session.get("max_cadence")

    # Elevation data
    workout_data["elevation_gain"] = session.get("total_ascent")
    workout_data["elevation_loss"] = session.get("total_descent")

    if "enhanced_min_altitude" in session:
        workout_data["altitude_min"] = session["enhanced_min_altitude"]
    else:
        workout_data["altitude_min"] = session.get("min_altitude")

    if "enhanced_max_altitude" in session:
        workout_data["altitude_max"] = session["enhanced_max_altitude"]
    else:
        workout_data["altitude_max"] = session.get("max_altitude")

    if "enhanced_avg_altitude" in session:
        workout_data["altitude_avg"] = session["enhanced_avg_altitude"]
    else:
        workout_data["altitude_avg"] = session.get("avg_altitude")

    # Grade metrics
    workout_data["grade_avg"] = session.get("avg_grade")
    workout_data["grade_max"] = session.get("max_pos_grade")
    workout_data["grade_min"] = session.get("max_neg_grade")

    # Temperature
    workout_data["temperature_avg"] = session.get("avg_temperature")
    workout_data["temperature_max"] = session.get("max_temperature")
    workout_data["temperature_min"] = session.get("min_temperature")

    for key, value in workout_data.items():
        setattr(workout, key, value)

    if not workout.summary:
        workout.summary = generate_cycling_workout_description(workout=workout)

    workout.save()


def validate_fit_file(fit_file):
    stream = Stream.from_byte_array(fit_file.read())
    decoder = Decoder(stream)

    if not decoder.is_fit():
        raise FitFileException(code="invalid_file", message="Invalid fit file")

    messages, errors = decoder.read()

    if errors:
        log.warning(
            "Encountered %s errors parsing a fit file. errors=%s", len(errors), errors
        )

    # Extract data from session messages
    if "session_mesgs" not in messages:
        raise FitFileException(code="no_sessions", message="Fit file has no sessions")

    session_messages = messages["session_mesgs"]

    if len(session_messages) != 1:
        raise FitFileException(
            code="session_count_mismatch",
            message=f"Fit file expects 1 session message, found {len(session_messages)}",
        )

    session = session_messages[0]

    if "sport" not in session:
        raise FitFileException(
            code="no_sport", message="Session does not contain a sport"
        )

    fit_file.seek(0)
    return messages


@atomic
def create_workout(actor, fit_file, name=None, summary=None):

    messages = validate_fit_file(fit_file)
    session = messages["session_mesgs"][0]
    workout_type = session["sport"]

    if not name:
        name = f"Workout on {datetime.datetime.now().strftime('%Y-%m-%d')}"

    if workout_type not in WORKOUT_TYPES_LIST:
        raise ValueError(f"Invalid workout {workout_type}")

    workout = Workout.objects.create(
        actor=actor,
        name=name,
        summary=summary,
        workout_type=workout_type,
        fit_file=fit_file,
    )

    local_path = reverse(
        "frontend-workout",
        kwargs={
            "webfinger": workout.actor.domainless_webfinger,
            "workout_id": workout.ap_id,
        },
    )

    # TODO: fugly, but it is what it is.
    workout.ap_uri = f"https://{settings.SITE_URL}{local_path}"
    workout.local_uri = workout.ap_uri
    workout.save()

    return workout


def process_workout(workout):

    messages = validate_fit_file(workout.fit_file)
    session = messages["session_mesgs"][0]

    # Initialize variables to store workout data
    workout_data = {
        "duration": 0,
        "distance_in_meters": 0,
        "start_time": None,
        "end_time": None,
    }

    if session["sport"] == "cycling":
        update_cycling_workout(workout, workout_data, session)
        workout.save()
        return

    raise ValueError("Unsupported sport in fit file.")
