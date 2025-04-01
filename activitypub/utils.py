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


def get_image_mimetype(image_field):
    """
    Helper method to determine MIME type from an image field
    """
    if not image_field:
        return None

    # Default to JPEG if we can't determine the type
    default_mime = "image/jpeg"

    try:
        # Try to get the file extension
        file_name = image_field.name
        file_ext = file_name.split(".")[-1].lower() if "." in file_name else ""

        # Map common extensions to MIME types
        mime_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "svg": "image/svg+xml",
        }

        return mime_types.get(file_ext, default_mime)
    except Exception:
        # If anything goes wrong, return default
        return default_mime
