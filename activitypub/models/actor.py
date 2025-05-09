from typing import List

from django.conf import settings
from django.db import models
from django.urls import reverse

from activitypub.utils import generate_ulid, get_image_mimetype


class Actor(models.Model):

    id = models.CharField(primary_key=True, default=generate_ulid, editable=False)
    webfinger = models.CharField(max_length=1024, unique=True)
    name = models.CharField(max_length=64)
    summary = models.TextField(null=True, blank=True)

    inbox_url = models.URLField(null=True, blank=True)
    outbox_url = models.URLField(null=True, blank=True)
    followers_url = models.URLField(null=True, blank=True)
    following_url = models.URLField(null=True, blank=True)
    actor_url = models.URLField(null=True, blank=True)
    profile_url = models.URLField(null=True, blank=True)
    shared_inbox_url = models.URLField(null=True, blank=True)

    is_remote = models.BooleanField(default=False)

    public_key = models.TextField(null=True, blank=True)
    private_key = models.TextField(null=True, blank=True)

    icon = models.ImageField(upload_to="icons", null=True, blank=True)
    header = models.ImageField(upload_to="headers", null=True, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.webfinger

    @property
    def domainless_webfinger(self):
        return self.webfinger.split("@")[0]

    @property
    def local_url(self):
        # TODO: this can be a field in the DB instead.
        path = reverse("frontend-profile", kwargs={"webfinger": self.webfinger})
        return f"https://{settings.SITE_URL}{path}"

    @property
    def followers_shared_inboxes(self) -> List[str]:
        """
        Returns the shared inboxes for followers who are on a remote server.
        """
        return (
            Actor.objects.filter(
                following__target=self,
                following__accepted=True,
                is_remote=True,
                shared_inbox_url__isnull=False,
            )
            .exclude(shared_inbox_url="")
            .values_list("shared_inbox_url", flat=True)
            .distinct()
        )

    @property
    def header_uri(self):
        if self.header:
            return self.header.url
        return "https://placehold.co/1200x300"

    @property
    def header_mimetype(self):
        if not self.header:
            return None
        return get_image_mimetype(self.icon)

    @property
    def icon_uri(self):
        if self.icon:
            return self.icon.url
        return "https://placehold.co/64"

    @property
    def icon_mimetype(self):
        if not self.icon:
            return None
        return get_image_mimetype(self.icon)
