import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F
from django.template.loader import render_to_string
from django.urls import reverse

from fedletic.models import EmailVerificationChallenge, FedleticUser
from fedletic.utils import create_secure_token


def create_email_verification_challenge(
    user: FedleticUser,
) -> EmailVerificationChallenge:
    if hasattr(user, "email_verification_challenge"):
        user.email_verification_challenge.delete()
    return EmailVerificationChallenge.objects.create(
        user=user, code=create_secure_token(n=6)
    )


def generate_and_send_verification_email(user: FedleticUser):
    # First, we mark the email address as unverified
    user.email_verified = False
    user.save()

    challenge = create_email_verification_challenge(user=user)
    confirmation_url = reverse("frontend-verify-email")
    confirmation_url = f"{settings.SITE_URL}{confirmation_url}?code={challenge.code}"

    message = render_to_string(
        "fedletic/email/verify-email.txt",
        context={
            "username": user.username,
            "code": challenge.code,
            "confirmation_url": confirmation_url,
        },
    )
    send_mail(
        subject="Verify your Fedletic account",
        from_email=settings.EMAIL_SENDER,
        message=message,
        recipient_list=[user.email],
    )


def verify_email(user: FedleticUser, code: str) -> bool:
    try:
        challenge = EmailVerificationChallenge.objects.get(user=user)
    except EmailVerificationChallenge.DoesNotExist:
        return False

    if challenge.code != code:
        EmailVerificationChallenge.objects.filter(user=user).update(
            attempts=F("attempts") + 1
        )
        return False

    # First, we have to mark the challenge as completed.
    challenge.completed_on = datetime.datetime.now(tz=datetime.timezone.utc)
    challenge.save()

    # And then mark the user verification as complete.
    user.email_verified = True
    user.save()

    return True
