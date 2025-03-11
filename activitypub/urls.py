from django.urls import path

from activitypub.views.actor import ActorView
from activitypub.views.followers import FollowersListView
from activitypub.views.following import FollowingListView
from activitypub.views.inbox import InboxView
from activitypub.views.nodeinfo import NodeInfoView
from activitypub.views.outbox import OutboxView
from activitypub.views.shared_inbox import SharedInboxView
from activitypub.views.well_known import WellKnownNodeInfoView, WellKnownWebFingerView

urlpatterns = [
    path("inbox/", SharedInboxView.as_view(), name="shared-inbox"),
    path("nodeinfo/2.0", NodeInfoView.as_view(), name="nodeinfo"),
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
    path(
        ".well-known/webfinger",
        WellKnownWebFingerView.as_view(),
        name="wellknown-webfinger",
    ),
    path(
        ".well-known/nodeinfo",
        WellKnownNodeInfoView.as_view(),
        name="wellknown-nodeinfo",
    ),
]
