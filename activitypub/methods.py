import logging
import os
from urllib.parse import urlencode, urlparse

import bleach
import httpx
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile

import activitypub.crypto as ap_crypto
from activitypub.exceptions import UsernameExists
from activitypub.models import Activity, Follower
from activitypub.models.actor import Actor
from activitypub.tasks.publish_activity import publish_activity
from activitypub.utils import get_actor_urls, webfinger_from_url

log = logging.getLogger(__name__)


def sanitize_html(html_content):
    if html_content is None:
        return ""

    sanitized_html = bleach.clean(
        html_content,
        tags=["p", "br", "strong", "em"],
        attributes={"a": ["href", "rel"]},
        strip=True,
    )
    return sanitized_html


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


def download_image_to_model(model, field_name, url):
    """
    Downloads an image from a URL and saves it to the specified model field.

    Args:
        model: Django model instance
        field_name: Name of the ImageField/FileField
        url: URL of the image to download

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the image content
        with httpx.Client() as client:
            response = client.get(url)
            response.raise_for_status()

        # Extract filename from URL
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)

        # If filename is empty or invalid, create a default one
        if not filename or "." not in filename:
            content_type = response.headers.get("Content-Type", "")
            ext = content_type.split("/")[-1]
            filename = f"image.{ext}"

        # Save to model field
        field = getattr(model, field_name)
        field.save(filename, ContentFile(response.content), save=True)

        return True
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False


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
        log.debug("Creating actor=%s", actor_data)

        shared_inbox = actor_data.get("endpoints", {}).get("sharedInbox")
        summary = sanitize_html(actor_data.get("summary", ""))

        # Create or update actor in local database
        actor, created = Actor.objects.update_or_create(
            profile_url=actor_url,
            defaults={
                "name": actor_data.get("name"),
                "summary": summary,
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

        if icon := actor_data.get("icon"):
            media_type = icon["mediaType"]
            if "image" in media_type:
                download_image_to_model(actor, "icon", icon["url"])

        # Mastodon calls header "image".
        if image := actor_data.get("image"):
            media_type = image["mediaType"]
            if "image" in media_type:
                download_image_to_model(actor, "header", image["url"])

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
    # Create the Follow activity
    activity = Activity.create_from_kwargs(
        actor=actor,
        target=target,
        activity_type="Follow",
        activity_object=target.actor_url,
    )

    publish_activity(activity_id=activity.pk, inbox_url=target.inbox_url)


def unfollow_actor(actor: Actor, target: Actor):
    # Create the Unfollow activity
    activity = Activity.create_from_kwargs(
        actor=actor,
        target=target,
        activity_type="Undo",
        activity_object={
            "type": "Follow",
            "actor": actor.actor_url,
            "object": target.actor_url,
        },
    )
    publish_activity(activity_id=activity.pk, inbox_url=target.inbox_url)
    log.info("Unfollowing actor=%s target=%s", actor, target)
    Follower.objects.filter(actor=actor, target=target).delete()
