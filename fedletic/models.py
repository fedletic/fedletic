from django.contrib.auth.models import AbstractUser
from django.db import models


class FedleticUser(AbstractUser):
    actor = models.OneToOneField(
        "activitypub.Actor", null=True, blank=True, on_delete=models.CASCADE
    )
