from django.core.management.base import BaseCommand

from cells.models import Cell, Level, LevelCell


LEVEL_CONFIG = [
    {
        "order": 1,
        "title": "Базовое распознавание клеток",
        "description": "Определение типа клетки по изображению",
        "badge": Level.Badge.BEGINNER,
        "cells": [],
    },
    {
        "order": 2,
        "title": "Соответствие клетки названию",
        "description": "Сопоставление изображения клетки соответственно названию",
        "badge": Level.Badge.INTERMEDIATE,
        "cells": [],
    },
    {
        "order": 3,
        "title": "Соответствие клеток",
        "description": "Сопоставление изображений клеток с их названиями",
        "badge": Level.Badge.INTERMEDIATE,
        "cells": [],
    },
    {
        "order": 4,
        "title": "Продвинутая гистология",
        "description": "Определение паталогий",
        "badge": Level.Badge.ADVANCED,
        "cells": [],
    },
    {
        "order": 5,
        "title": "Экспертный подсчёт",
        "description": "Подсчёт клеток",
        "badge": Level.Badge.EXPERT,
        "cells": [],
    },
]


class Command(BaseCommand):
    help = "Create initial test levels"

    def handle(self, *args, **options):
        for item in LEVEL_CONFIG:
            level, _ = Level.objects.update_or_create(
                order=item["order"],
                defaults={
                    "title": item["title"],
                    "description": item["description"],
                    "badge": item["badge"],
                    "required_completions": 5,
                    "question_count": 10,
                    "is_active": True,
                },
            )

            if item["cells"]:
                existing_ids = set(
                    level.level_cells.values_list("cell_id", flat=True)
                )
                for cell_name in item["cells"]:
                    cell = Cell.objects.filter(name=cell_name).first()
                    if cell and cell.id not in existing_ids:
                        LevelCell.objects.create(level=level, cell=cell)

        self.stdout.write(self.style.SUCCESS("Levels seeded"))