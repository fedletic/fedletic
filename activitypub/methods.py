import logging

import httpx
from django.conf import settings
from django.core.cache import cache

import activitypub.crypto as ap_crypto
from activitypub.exceptions import UsernameExists
from activitypub.models.actor import Actor
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
