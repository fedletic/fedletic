import time

from django.conf import settings


def cache_buster(request):
    return {"cache_buster": hex(int(time.time() * 1000))}


def various(request):
    return {"version": settings.VERSION}
