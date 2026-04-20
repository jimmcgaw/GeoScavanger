from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Bulk import audio clips from JSON or CSV. Implementation deferred."

    def handle(self, *args, **options) -> None:
        self.stdout.write(self.style.WARNING("import_clips is not implemented yet."))
