from django.conf import settings
from django.db import models


class Cell(models.Model):
    name = models.CharField(max_length=255)
    latin_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class CellImage(models.Model):
    cell = models.ForeignKey(
        Cell,
        on_delete=models.CASCADE,
        related_name="cell_images",
    )
    image = models.ImageField(upload_to="cells/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.image.name


class Level(models.Model):
    class QuestionType(models.TextChoices):
        IMAGE_TO_NAME = "image_to_name", "Image → Name"
        NAME_TO_IMAGE = "name_to_image", "Name → Image"
        MATCHING = "matching", "Matching"

    class Badge(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        EXPERT = "expert", "Expert"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(unique=True)
    badge = models.CharField(
        max_length=30,
        choices=Badge.choices,
        default=Badge.BEGINNER,
    )
    question_type = models.CharField(
        max_length=30,
        choices=QuestionType.choices,
        default=QuestionType.IMAGE_TO_NAME,
    )
    required_completions = models.PositiveIntegerField(default=5)
    passing_percent = models.PositiveSmallIntegerField(default=70)
    question_count = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Level {self.order}: {self.title}"


class LevelCell(models.Model):
    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        related_name="level_cells",
    )
    cell = models.ForeignKey(
        Cell,
        on_delete=models.CASCADE,
        related_name="cell_levels",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["level", "cell"],
                name="uq_level_cell",
            )
        ]

    def __str__(self):
        return f"{self.level} → {self.cell}"


class UserLevelProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="level_progress",
    )
    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        related_name="user_progress",
    )
    completions_count = models.PositiveIntegerField(default=0)
    best_score = models.PositiveIntegerField(default=0)
    last_score = models.PositiveIntegerField(default=0)
    is_unlocked = models.BooleanField(default=False)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "level"],
                name="uq_user_level_progress",
            )
        ]
        ordering = ["level__order"]

    def __str__(self):
        return f"{self.user} - {self.level} ({self.completions_count})"

    @property
    def is_completed(self):
        return self.completions_count >= self.level.required_completions

    @property
    def completion_percent(self):
        if self.level.required_completions == 0:
            return 0
        return int((self.completions_count / self.level.required_completions) * 100)


class TestSession(models.Model):
    class Mode(models.TextChoices):
        RANDOM = "random", "Random"
        TRAINER = "trainer", "Trainer"
        LEVEL = "level", "Level"

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
    level = models.ForeignKey(
        Level,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )
    level_attempt_number = models.PositiveSmallIntegerField(null=True, blank=True)
    level_completion_recorded = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Session {self.id} - {self.user} - {self.mode}"


class TestSessionImage(models.Model):
    class Source(models.TextChoices):
        RANDOM = "random", "Random"
        PERSONAL_ERROR = "personal_error", "Personal error"
        SIMILAR = "similar", "Similar"
        NOVEL = "novel", "Novel"
        LEVEL = "level", "Level"

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
        on_delete=models.CASCADE,
    )
    total_attempts = models.PositiveIntegerField(default=0)
    total_correct = models.PositiveIntegerField(default=0)