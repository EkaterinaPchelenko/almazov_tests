from django.core.management.base import BaseCommand
from cells.services.similarity import rebuild_image_similarity


class Command(BaseCommand):
    help = "Rebuild item-based image similarity matrix"

    def handle(self, *args, **options):
        rebuild_image_similarity()
        self.stdout.write(self.style.SUCCESS("Image similarity rebuilt"))