from django.db import models


class Cell(models.Model):
    name = models.CharField(max_length=255)  # Официальное название
    latin_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class CellImage(models.Model):
    cell = models.ForeignKey(
        Cell,
        on_delete=models.CASCADE,
        related_name="cell_image"
    )
    image = models.ImageField(upload_to="cells/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.image.name
# Create your models here.
