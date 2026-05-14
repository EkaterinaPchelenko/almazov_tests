import os
import unicodedata

from django.core.files import File
from django.core.management.base import BaseCommand

from cells.models import DiagnosticCase, DiagnosticCaseImage


def sanitize_filename(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    return name.lower()


def get_order_number(filename):
    name, _ = os.path.splitext(filename)

    try:
        return int(name)
    except ValueError:
        return 9999


class Command(BaseCommand):
    help = "Import diagnostic case images from folders into storage"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            type=str,
            help="Path to root folder with diagnostic case images",
        )

    def handle(self, *args, **kwargs):
        root_path = kwargs["path"]

        if not os.path.exists(root_path):
            self.stdout.write(self.style.ERROR("Path does not exist"))
            return

        for folder_name in os.listdir(root_path):
            folder_path = os.path.join(root_path, folder_name)

            if not os.path.isdir(folder_path):
                continue

            case = DiagnosticCase.objects.filter(title=folder_name).first()

            if not case:
                self.stdout.write(
                    self.style.WARNING(
                        f"Case not found for folder: {folder_name}"
                    )
                )
                continue

            DiagnosticCaseImage.objects.filter(case=case).delete()

            filenames = [
                filename
                for filename in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, filename))
            ]

            filenames.sort(key=get_order_number)

            for index, filename in enumerate(filenames, start=1):
                file_path = os.path.join(folder_path, filename)
                sanitized_name = sanitize_filename(filename)

                with open(file_path, "rb") as f:
                    django_file = File(
                        f,
                        name=f"{sanitize_filename(case.title)}_{index}_{sanitized_name}",
                    )

                    DiagnosticCaseImage.objects.create(
                        case=case,
                        image=django_file,
                        order_number=index,
                    )

                self.stdout.write(
                    f"Uploaded {case.title}: image #{index} — {sanitized_name}"
                )

        self.stdout.write(self.style.SUCCESS("Diagnostic case images import completed"))