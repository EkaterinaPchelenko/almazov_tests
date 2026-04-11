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
    class Mode(models.TextChoices):
        RANDOM = "random", "Random"
        TRAINER = "trainer", "Trainer"

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="test_sessions",
    )
    mode = models.CharField(max_length=20, choices=Mode.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Session {self.id} - {self.user.email} - {self.mode}"


class TestSessionImage(models.Model):
    class Source(models.TextChoices):
        RANDOM = "random", "Random"
        PERSONAL_ERROR = "personal_error", "Personal error"
        SIMILAR = "similar", "Similar"
        NOVEL = "novel", "Novel"

    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name="session_images",
    )
    image = models.ForeignKey(CellImage, on_delete=models.CASCADE)
    order_number = models.PositiveIntegerField()
    source = models.CharField(
        max_length=30,
        choices=Source.choices,
        default=Source.RANDOM,
    )
    score_snapshot = models.FloatField(default=0.0)
    is_answered = models.BooleanField(default=False)

    class Meta:
        ordering = ["order_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "order_number"],
                name="uq_session_order_number",
            ),
            models.UniqueConstraint(
                fields=["session", "image"],
                name="uq_session_image",
            ),
        ]


class UserImageAnswer(models.Model):
    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    session_image = models.OneToOneField(
        TestSessionImage,
        on_delete=models.CASCADE,
        related_name="answer",
    )
    image = models.ForeignKey(CellImage, on_delete=models.CASCADE)
    order_number = models.PositiveIntegerField()
    user_answer = models.CharField(max_length=255)
    normalized_answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class UserImagePerformance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ForeignKey(CellImage, on_delete=models.CASCADE)
    total_attempts = models.PositiveIntegerField(default=0)
    correct_attempts = models.PositiveIntegerField(default=0)
    wrong_attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "image"],
                name="uq_user_image_performance",
            )
        ]
        indexes = [
            models.Index(fields=["user", "image"]),
            models.Index(fields=["user", "last_attempt_at"]),
            models.Index(fields=["image"]),
        ]

    @property
    def error_rate(self):
        if self.total_attempts == 0:
            return 0.0
        return self.wrong_attempts / self.total_attempts


class ImageSimilarity(models.Model):
    image_from = models.ForeignKey(
        CellImage,
        on_delete=models.CASCADE,
        related_name="similarity_from",
    )
    image_to = models.ForeignKey(
        CellImage,
        on_delete=models.CASCADE,
        related_name="similarity_to",
    )
    similarity_score = models.FloatField(default=0)
    common_users_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["image_from", "image_to"],
                name="uq_image_similarity_pair",
            ),
            models.CheckConstraint(
                check=~models.Q(image_from=models.F("image_to")),
                name="chk_similarity_not_self",
            ),
        ]
        indexes = [
            models.Index(fields=["image_from", "similarity_score"]),
            models.Index(fields=["image_to"]),
        ]


class GlobalImageStats(models.Model):
    image = models.OneToOneField(
        CellImage,
        on_delete=models.CASCADE
    )

    total_attempts = models.PositiveIntegerField(default=0)
    total_correct = models.PositiveIntegerField(default=0)