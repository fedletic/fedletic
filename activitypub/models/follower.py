from django.db import models


class Follower(models.Model):
    actor = models.ForeignKey(
        "activitypub.Actor", on_delete=models.CASCADE, related_name="following"
    )
    target = models.ForeignKey(
        "activitypub.Actor", on_delete=models.CASCADE, related_name="followers"
    )
    followed_on = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=True)

    class Meta:
        unique_together = ("actor", "target")  # Prevent duplicate follows

    def accept(self):
        self.accepted = True
        self.save()

    def __str__(self):
        return f"{self.actor} -> {self.target}"
