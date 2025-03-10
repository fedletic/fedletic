from dataclasses import dataclass

from activitypub.objects import ActivityPubObject


@dataclass
class FollowObject(ActivityPubObject):
    actor: str
    object: str
