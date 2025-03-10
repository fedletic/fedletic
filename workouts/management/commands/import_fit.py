import logging
import pprint

from django.core.management.base import BaseCommand
from garmin_fit_sdk import Decoder, Stream

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Description of what the import_fit command does"

    def add_arguments(self, parser):
        parser.add_argument("--filename", required=True, help="Fit file location")

    def handle(self, filename, *args, **options):
        # Command implementation goes here
        self.stdout.write("Running import_fit command")

        # Example success message:
        self.stdout.write(
            self.style.SUCCESS("import_fit command completed successfully")
        )

        stream = Stream.from_file(filename)
        decoder = Decoder(stream)
        messages, errors = decoder.read()

        pprint.pprint(errors)
        pprint.pprint(messages)
