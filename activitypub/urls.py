from django.urls import path

from activitypub.views.actor import ActorView
from activitypub.views.followers import FollowersListView
from activitypub.views.following import FollowingListView
from activitypub.views.inbox import InboxView
from activitypub.views.outbox import OutboxView
from activitypub.views.shared_inbox import SharedInboxView
from activitypub.views.webfinger import WebFingerView

urlpatterns = [
    path("inbox/", SharedInboxView.as_view(), name="shared-inbox"),
    path("users/<str:username>", ActorView.as_view(), name="actor"),
    path("users/<str:username>/inbox/", InboxView.as_view(), name="inbox"),
    path("users/<str:username>/outbox/", OutboxView.as_view(), name="outbox"),
    path(
        "users/<str:username>/followers/",
        FollowersListView.as_view(),
        name="followers-list",
    ),
    path(
        "users/<str:username>/following/",
        FollowingListView.as_view(),
        name="following-list",
    ),
    path(".well-known/webfinger", WebFingerView.as_view(), name="webfinger"),
]
