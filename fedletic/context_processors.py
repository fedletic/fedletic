import time


def cache_buster(request):
    return {"cache_buster": hex(int(time.time() * 1000))}
