import logging
from urllib.parse import urlparse

import ulid
from django.conf import settings

log = logging.getLogger(__name__)


def generate_ulid():
    """Returns a new ULID as a string."""
    return str(ulid.new()).lower()


def webfinger_from_url(actor_url: str) -> str:
    parsed_url = urlparse(actor_url)
    domain = parsed_url.netloc
    username = actor_url.split("/")[-1]
    return f"{username}@{domain}"


def get_actor_urls(username):
    """Returns a dictionary of ActivityPub URLs for a given username."""
    base_url = f"https://{settings.SITE_URL}/users/{username}"

    return {
        "actor": base_url,
        "inbox": f"{base_url}/inbox/",
        "outbox": f"{base_url}/outbox/",
        "followers": f"{base_url}/followers/",
        "following": f"{base_url}/following/",
    }
