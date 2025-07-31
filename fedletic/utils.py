import secrets
import string


def create_secure_token(n=6):
    """Generate a cryptographically secure 6-character verification code."""
    characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(characters) for _ in range(n))
