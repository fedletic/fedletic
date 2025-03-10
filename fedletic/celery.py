import os

import dotenv
from celery import Celery

dotenv.load_dotenv(override=True)
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fedletic.settings")

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_DB = os.environ.get("REDIS_DB", "0")

app = Celery(
    "fedletic",
    broker=f"redis://{REDIS_HOST}:6379/{REDIS_DB}",
    backend=f"redis://{REDIS_HOST}:6379/{REDIS_DB}",
    broker_connection_retry_on_startup=True,
)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
