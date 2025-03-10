from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from activitypub.models.actor import Actor
from activitypub.models.follower import Follower
from activitypub.views import ActivityPubBaseView


class FollowingListView(ActivityPubBaseView):
    def get(self, request, username):
        # TODO: Paging
        user = get_object_or_404(Actor, webfinger=f"{username}@{settings.SITE_URL}")
        following = Follower.objects.filter(actor=user)

        return JsonResponse(
            {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"https://{settings.SITE_URL}/users/{username}/following",
                "type": "OrderedCollection",
                "totalItems": following.count(),
                "items": [follow.target.profile_url for follow in following],
            }
        )
