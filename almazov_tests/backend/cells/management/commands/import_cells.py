import os
import unicodedata
from django.core.management.base import BaseCommand
from django.core.files import File
from cells.models import Cell, CellImage

def sanitize_filename(name):
    # Транслитерация и удаление спецсимволов
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    return name.lower()

class Command(BaseCommand):
    help = "Import cell images from folder into MinIO"

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            type=str,
            help='Path to root folder with cell images'
        )

    def handle(self, *args, **kwargs):
        root_path = kwargs['path']

        if not os.path.exists(root_path):
            self.stdout.write(self.style.ERROR("Path does not exist"))
            return

        for folder_name in os.listdir(root_path):
            folder_path = os.path.join(root_path, folder_name)

            if not os.path.isdir(folder_path):
                continue

            # Создаём или получаем Cell
            cell, created = Cell.objects.get_or_create(
                name=folder_name
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created Cell: {folder_name}"))

            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)

                if not os.path.isfile(file_path):
                    continue

                sanitized_name = sanitize_filename(filename)

                with open(file_path, 'rb') as f:
                    django_file = File(f, name=sanitized_name)

                    image = CellImage.objects.create(
                        cell=cell,
                        image=django_file
                    )

                self.stdout.write(f"Uploaded: {sanitized_name}")

        self.stdout.write(self.style.SUCCESS("Import completed"))