import importlib

from django.apps import AppConfig


class ActivitypubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "activitypub"

    def ready(self):
        """
        Import events modules from all installed apps to register event handlers
        when Django starts.
        """
        # Import our event system first

        # Get all installed apps
        from django.apps import apps

        # Loop through all installed apps
        for app_config in apps.get_app_configs():
            # Construct the module path for potential events.py in each app
            module_path = f"{app_config.name}.events"

            try:
                # Try importing the events module
                importlib.import_module(module_path)
            except ImportError:
                # Skip if the app doesn't have an events module
                pass
