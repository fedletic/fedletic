import json
import logging

import httpx

from activitypub.crypto import create_http_signature
from activitypub.models.activity import Activity
from fedletic.celery import app

log = logging.getLogger(__name__)


@app.task
def publish_activity(activity_id, inbox_url: str = None):
    activity = Activity.objects.get(pk=activity_id)

    if activity.is_remote:
        raise ValueError("Cannot send activities originating from remote")

    # Send the activity to the remote inbox with HTTP Signatures
    headers = {
        "Content-Type": "application/activity+json",
        "Accept": "application/activity+json",
    }

    # Add HTTP Signature
    activity_json = activity.to_activity_json()
    inbox_url = activity.target.inbox_url if activity.target else inbox_url

    if not inbox_url:
        raise ValueError("Missing inbox url")

    log.info(
        "Ready to publish to inbox=%s content=%s",
        inbox_url,
        activity_json,
    )
    encoded_body = json.dumps(activity_json).encode("utf-8")
    signature = create_http_signature(
        actor=activity.actor,
        target_url=inbox_url,
        data=encoded_body,
    )
    headers.update(signature)

    response = httpx.post(
        inbox_url,
        content=encoded_body,  # Use the same bytes we calculated the digest on
        headers=headers,
    )

    if response.status_code >= 400:
        log.error(
            "Failed to send activity=%s inbox=%s status=%s response=%s",
            activity.id,
            inbox_url,
            response.status_code,
            response.text,
        )
    else:
        log.info(
            "Sent activity=%s inbox=%s, status=%s response=%s",
            activity.id,
            inbox_url,
            response.status_code,
            response.text,
        )
