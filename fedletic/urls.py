from urllib.parse import urlparse

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

import apis.v1.urls
from frontend.views import (
    CreateWorkoutView,
    EditProfileView,
    FeedView,
    FollowersView,
    FollowingView,
    LandingView,
    LoginView,
    LogoutView,
    ProfileView,
    RegisterView,
    WorkoutNoteView,
    WorkoutView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("activitypub.urls")),
    path("", LandingView.as_view(), name="frontend-landing"),
    path("api/v1/", include(apis.v1.urls), name="api_v1"),
    path("oauth/", include("oauth2_provider.urls", namespace="oauth2_provider")),
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
    path("profile", EditProfileView.as_view(), name="frontend-edit-profile"),
    path("accounts/login", LoginView.as_view(), name="frontend-login"),
    path("accounts/logout", LogoutView.as_view(), name="frontend-logout"),
    path("accounts/register", RegisterView.as_view(), name="frontend-register"),
    path(
        "workouts/create/", CreateWorkoutView.as_view(), name="frontend-workout-create"
    ),
]

if settings.DEBUG:
    media_path = urlparse(settings.MEDIA_URL).path
    urlpatterns += static(media_path, document_root=settings.MEDIA_ROOT)
