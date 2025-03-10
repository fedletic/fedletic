from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from activitypub.models.actor import Actor
from activitypub.models.follower import Follower
from activitypub.views import ActivityPubBaseView


class FollowersListView(ActivityPubBaseView):
    # TODO: Paging

    def get(self, request, username):
        user = get_object_or_404(Actor, webfinger=f"{username}@{settings.SITE_URL}")
        followers = Follower.objects.filter(target=user)

        return JsonResponse(
            {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"https://{settings.SITE_URL}/users/{username}/followers",
                "type": "OrderedCollection",
                "totalItems": followers.count(),
                "items": [follower.actor.profile_url for follower in followers],
            }
        )
