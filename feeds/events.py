from activitypub.events import events


@events.on("activity")
def foo(**kwargs):
    pass
