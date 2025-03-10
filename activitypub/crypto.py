import base64
import logging
from datetime import datetime
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
)

from activitypub import methods as ap_methods
from activitypub import utils as ap_utils
from activitypub.models.actor import Actor

log = logging.getLogger(__name__)
SIGNATURE_HEADER = "(request-target) host date digest"


def create_digest(data: bytes):
    digest = hashes.Hash(hashes.SHA256())
    digest.update(data)
    digest_value = digest.finalize()
    digest_b64 = base64.b64encode(digest_value).decode()
    return f"SHA-256={digest_b64}"


def create_http_signature(actor, target_url, data):

    parsed_url = urlparse(target_url)
    host = parsed_url.netloc
    path = parsed_url.path

    # Get the private key
    if not actor.private_key:
        raise ValueError("Actor doesn't have a private key")

    private_key = load_pem_private_key(actor.private_key.encode(), password=None)
    request_target = f"post {path}"
    date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
    digest = create_digest(data)

    signature_string = f"(request-target): {request_target}\nhost: {host}\ndate: {date}\ndigest: {digest}"

    signature = private_key.sign(
        signature_string.encode(), padding.PKCS1v15(), hashes.SHA256()
    )
    signature_b64 = base64.b64encode(signature).decode()

    # Create the Signature header
    key_id = f"{actor.actor_url}#main-key"
    signature_header = f'keyId="{key_id}",algorithm="rsa-sha256",headers="(request-target) host date digest",signature="{signature_b64}"'

    return {"Host": host, "Date": date, "Digest": digest, "Signature": signature_header}


def verify_http_signature(request):
    """Verifies an incoming HTTP Signature using RSA."""
    signature_header = request.headers.get("signature")
    if not signature_header:
        return False, "Missing Signature Header"

    # Parse signature header
    sig_parts = {}
    for part in signature_header.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        sig_parts[key.strip()] = value.strip('"')

    if (
        "signature" not in sig_parts
        or "keyId" not in sig_parts
        or "headers" not in sig_parts
    ):
        return False, "Incomplete signature header"

    signature_b64 = sig_parts["signature"]
    key_id = sig_parts["keyId"]
    headers_list = sig_parts["headers"].split(" ")

    # Fetch the actor - handle remote actors correctly
    actor_url = key_id.replace("#main-key", "")

    # Log incoming signature details for debugging
    log.info(f"Actor URL from keyId: {actor_url}")
    log.info(f"Headers to verify: {headers_list}")
    log.info(f"Full headers={dict(request.headers)}")

    # Find actor by URL, not just username
    # You'll need to adjust this based on your Actor model structure
    actor = Actor.objects.filter(profile_url=actor_url).first()

    # If not found directly, try fetching the remote actor
    if not actor:
        # Extract domain from actor_url to handle remote identities
        username = ap_utils.webfinger_from_url(actor_url)
        # Try to find by username and domain
        actor = Actor.objects.filter(webfinger=username).first()

        # If still not found, fetch from remote
        if not actor:
            actor = ap_methods.fetch_remote_actor(actor_url)

    if not actor:
        log.warning("Failed to find or fetch actor_url=%s", actor_url)
        return False, "Actor not found"

    # Load public key
    try:
        public_key = load_pem_public_key(actor.public_key.encode())
        log.info(f"Successfully loaded public key for {actor.webfinger}")
    except Exception as e:
        log.warning("Invalid public key for actor=%s: %s", actor.id, str(e))
        return False, f"Invalid public key: {str(e)}"

    # Reconstruct signing string - exactly as specified in headers_list order
    signing_parts = []
    for header in headers_list:
        if header == "(request-target)":
            method = request.method.lower()
            path = request.path
            signing_parts.append(f"(request-target): {method} {path}")
        else:
            header_value = request.headers.get(header)
            if not header_value:
                log.warning("Missing required header=%s", header)
                return False, f"Missing required header: {header}"
            signing_parts.append(f"{header.lower()}: {header_value}")

    signing_string = "\n".join(signing_parts)

    # Log the reconstructed signing string for debugging
    log.info(f"Reconstructed signing string: {signing_string}")

    # Verify signature
    try:
        public_key.verify(
            base64.b64decode(signature_b64),
            signing_string.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        log.info(f"Signature verified successfully for {actor.webfinger}")
        return True, "Valid signature"
    except Exception as e:
        log.warning(
            "Invalid signature for actor=%s: %s",
            actor.profile_url,
            str(e),
        )
        # Add detailed debugging information
        log.debug(f"Signature: {signature_b64}")
        log.debug(f"Signing string: {signing_string}")
        return False, f"Invalid signature: {str(e)}"


def generate_keys():
    # Generate RSA key pair
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    # Get public key
    public_key = private_key.public_key()

    # Store public key in PEM format
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8"), public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode(
        "utf-8"
    )
