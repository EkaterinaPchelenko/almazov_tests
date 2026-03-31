from cells.models import CellImage

def generate_random_images(limit=10):
    return list(CellImage.objects.order_by("?")[:limit])