from django.contrib import admin
from django.urls import include, path

from frontend.views import (
    CreateWorkoutView,
    FeedView,
    FollowersView,
    FollowingView,
    LandingView,
    LogoutView,
    ProfileView,
    WorkoutNoteView,
    WorkoutView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("activitypub.urls")),
    path("", LandingView.as_view(), name="frontend-landing"),
    path("@<str:webfinger>", ProfileView.as_view(), name="frontend-profile"),
    path(
        "@<str:webfinger>/following",
        FollowingView.as_view(),
        name="frontend-following",
    ),
    path(
        "@<str:webfinger>/followers",
        FollowersView.as_view(),
        name="frontend-followers",
    ),
    path(
        "@<str:webfinger>/<str:workout_id>",
        WorkoutView.as_view(),
        name="frontend-workout",
    ),
    path(
        "@<str:webfinger>/<str:workout_id>/note",
        WorkoutNoteView.as_view(),
        name="frontend-workout-note",
    ),
    path("feed", FeedView.as_view(), name="frontend-feed"),
    path("logout", LogoutView.as_view(), name="frontend-logout"),
    path(
        "workouts/create/", CreateWorkoutView.as_view(), name="frontend-workout-create"
    ),
]
