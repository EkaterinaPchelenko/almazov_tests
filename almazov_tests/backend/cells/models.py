from django.db import models
from django.conf import settings


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


class TestSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="test_sessions"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Session {self.id} - {self.user.email}"


class UserImageAnswer(models.Model):
    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    image = models.ForeignKey(
        CellImage,
        on_delete=models.CASCADE
    )
    user_answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)


class UserImagePerformance(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    image = models.ForeignKey(
        CellImage,
        on_delete=models.CASCADE
    )

    total_attempts = models.PositiveIntegerField(default=0)
    correct_attempts = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "image")


class ImageSimilarity(models.Model):
    image_from = models.ForeignKey(
        CellImage,
        on_delete=models.CASCADE,
        related_name="similarity_from"
    )
    image_to = models.ForeignKey(
        CellImage,
        on_delete=models.CASCADE,
        related_name="similarity_to"
    )
    similarity_score = models.FloatField(default=0)

    class Meta:
        unique_together = ("image_from", "image_to")


class GlobalImageStats(models.Model):
    image = models.OneToOneField(
        CellImage,
        on_delete=models.CASCADE
    )

    total_attempts = models.PositiveIntegerField(default=0)
    total_correct = models.PositiveIntegerField(default=0)