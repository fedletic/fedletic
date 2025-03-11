import logging
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.core.cache import cache

import activitypub.crypto as ap_crypto
from activitypub.exceptions import UsernameExists
from activitypub.models import Activity
from activitypub.models.actor import Actor
from activitypub.tasks.publish_activity import publish_activity
from activitypub.utils import get_actor_urls, webfinger_from_url

log = logging.getLogger(__name__)


def create_actor(username):

    webfinger = f"{username}@{settings.SITE_URL}"
    if Actor.objects.filter(webfinger=webfinger).exists():
        raise UsernameExists()

    urls = get_actor_urls(username)
    private_key, public_key = ap_crypto.generate_keys()
    profile_url = f"https://{settings.SITE_URL}/@{webfinger}"

    actor = Actor.objects.create(
        webfinger=webfinger,
        name=username,
        profile_url=profile_url,
        actor_url=urls["actor"],
        inbox_url=urls["inbox"],
        outbox_url=urls["outbox"],
        followers_url=urls["followers"],
        following_url=urls["following"],
        private_key=private_key,
        public_key=public_key,
    )

    return actor


def webfinger_lookup(user_id):
    """
    Perform a WebFinger lookup for a Fediverse user.

    Args:
        user_id (str): The user ID in the format username@domain.tld

    Returns:
        dict: The WebFinger JSON response data

    Raises:
        ValueError: If the user_id format is invalid
        httpx.HTTPError: If the HTTP request fails
    """
    if "@" not in user_id:
        raise ValueError("User ID must be in the format username@domain.tld")

    _, domain = user_id.split("@", 1)

    base_url = f"https://{domain}/.well-known/webfinger"
    params = {"resource": f"acct:{user_id}"}
    url = f"{base_url}?{urlencode(params)}"
    headers = {"Accept": "application/jrd+json, application/json"}
    response = httpx.get(url, follow_redirects=True, headers=headers)
    response.raise_for_status()

    # Return the JSON response
    return response.json()


def fetch_remote_actor(actor_url):
    """
    Fetch and cache a remote actor from its URL

    Args:
        actor_url: The URL of the actor to fetch

    Returns:
        Actor object or None if not found
    """
    # Check cache first
    cache_key = f"remote_actor:{actor_url}"
    cached_actor = cache.get(cache_key)
    if cached_actor:
        return cached_actor

    # Make HTTP request to fetch the actor
    try:
        headers = {
            "Accept": "application/activity+json",
            "User-Agent": "YourApp/1.0",  # Replace with your app name/version
        }

        response = httpx.get(actor_url, headers=headers, timeout=10)
        response.raise_for_status()
        actor_data = response.json()

        # Extract required data
        username = webfinger_from_url(actor_url)
        public_key = actor_data.get("publicKey", {}).get("publicKeyPem")

        if not public_key:
            log.warning(f"No public key found for {actor_url}")
            return None

        shared_inbox = actor_data.get("endpoints", {}).get("sharedInbox")

        # Create or update actor in local database
        actor, created = Actor.objects.update_or_create(
            profile_url=actor_url,
            defaults={
                "webfinger": username,
                "public_key": public_key,
                "is_remote": True,
                "inbox_url": actor_data.get("inbox"),
                "shared_inbox_url": shared_inbox,
                "outbox_url": actor_data.get("outbox"),
                "followers_url": actor_data.get("followers"),
                "following_url": actor_data.get("following"),
                "actor_url": actor_data.get("id"),
                "profile_url": actor_data.get("url"),
            },
        )

        # Cache the actor for future requests
        cache.set(cache_key, actor, timeout=3600)  # Cache for 1 hour

        return actor

    except Exception as e:
        log.error(f"Error fetching remote actor {actor_url}: {str(e)}")
        return None


def follow_actor(actor: Actor, target: Actor):
    """
    Creates a Follow activity from one actor to another.

    Args:
        actor (Actor): The actor initiating the follow request
        target (Actor): The actor being followed

    Returns:
        Activity: The created Follow activity
    """
    # Standard ActivityPub context
    context = ["https://www.w3.org/ns/activitystreams"]

    # Create the Follow activity
    activity = Activity.create_from_kwargs(
        actor=actor,
        target=target,
        context=context,
        activity_type="Follow",
        activity_object=target.actor_url,
    )

    publish_activity(activity_id=activity.pk, inbox_url=target.inbox_url)
