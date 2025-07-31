from django.contrib.auth.models import AbstractUser
from django.db import models


class FedleticUser(AbstractUser):
    actor = models.OneToOneField(
        "activitypub.Actor", null=True, blank=True, on_delete=models.CASCADE
    )
    email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, null=True, blank=True)


class EmailVerificationChallenge(models.Model):
    user = models.OneToOneField(
        FedleticUser,
        related_name="email_verification_challenge",
        on_delete=models.CASCADE,
    )
    code = models.CharField(max_length=6)
    created_on = models.DateTimeField(auto_now_add=True)
    completed_on = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
