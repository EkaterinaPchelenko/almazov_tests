import random

from cells.models import CellImage


def generate_random_images(limit: int = 10):
    images = list(CellImage.objects.select_related("cell").all())
    random.shuffle(images)
    return images[:limit]