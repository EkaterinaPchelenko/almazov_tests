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
    duration_seconds = models.PositiveIntegerField(default=0)
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


class GlobalImageStats(models.Model):
    image = models.OneToOneField(
        CellImage,
        on_delete=models.CASCADE,
    )
    total_attempts = models.PositiveIntegerField(default=0)
    total_correct = models.PositiveIntegerField(default=0)


class DiagnosticCase(models.Model):
    title = models.CharField(max_length=255)
    diagnosis = models.CharField(max_length=255)
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title


class DiagnosticCaseExpectedCount(models.Model):
    case = models.ForeignKey(
        DiagnosticCase,
        on_delete=models.CASCADE,
        related_name="expected_counts",
    )
    cell = models.ForeignKey(
        Cell,
        on_delete=models.CASCADE,
        related_name="diagnostic_expected_counts",
    )
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["case", "cell"],
                name="uq_diagnostic_case_expected_cell",
            )
        ]

    def __str__(self):
        return f"{self.case} — {self.cell}: {self.count}"


class DiagnosticCaseImage(models.Model):
    case = models.ForeignKey(
        DiagnosticCase,
        on_delete=models.CASCADE,
        related_name="case_images",
    )
    image = models.ImageField(upload_to="diagnostic_cases/")
    order_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "order_number"],
                name="uq_diagnostic_case_image_order",
            )
        ]

    def __str__(self):
        return f"{self.case} — image #{self.order_number}"


class DiagnosticCaseProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    case = models.ForeignKey(
        DiagnosticCase,
        on_delete=models.CASCADE,
        related_name="user_progress",
    )

    is_completed = models.BooleanField(default=False)
    attempts_count = models.PositiveIntegerField(default=0)

    last_attempt_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "case"],
                name="uq_user_diagnostic_case_progress",
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.case} — completed={self.is_completed}"


class DiagnosticCaseSession(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        AWAITING_DIAGNOSIS = "awaiting_diagnosis", "Awaiting diagnosis"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    case = models.ForeignKey(
        DiagnosticCase,
        on_delete=models.CASCADE,
        related_name="sessions",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )

    current_offset = models.PositiveIntegerField(default=0)
    batch_size = models.PositiveIntegerField(default=5)

    counts_are_correct = models.BooleanField(default=False)
    diagnosis_is_correct = models.BooleanField(default=False)

    selected_diagnosis = models.CharField(max_length=255, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user} — {self.case} — {self.status}"


class DiagnosticCaseImageAnswer(models.Model):
    session = models.ForeignKey(
        DiagnosticCaseSession,
        on_delete=models.CASCADE,
        related_name="image_answers",
    )
    case_image = models.ForeignKey(
        DiagnosticCaseImage,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    selected_cell = models.ForeignKey(
        Cell,
        on_delete=models.CASCADE,
        related_name="diagnostic_selected_answers",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "case_image"],
                name="uq_diagnostic_session_image_answer",
            )
        ]

    def __str__(self):
        return f"{self.session} — {self.case_image} → {self.selected_cell}"



class DiagnosticFinding(models.Model):
    title = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class DiagnosticCaseExpectedFinding(models.Model):
    case = models.ForeignKey(
        DiagnosticCase,
        on_delete=models.CASCADE,
        related_name="expected_findings",
    )
    finding = models.ForeignKey(
        DiagnosticFinding,
        on_delete=models.CASCADE,
        related_name="case_expected_findings",
    )
    expected_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["finding__title"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "finding"],
                name="uq_diagnostic_case_expected_finding",
            )
        ]

    def __str__(self):
        return f"{self.case} — {self.finding.title}: {self.expected_count}"


class DiagnosticCaseFindingAnswer(models.Model):
    session = models.ForeignKey(
        DiagnosticCaseSession,
        on_delete=models.CASCADE,
        related_name="finding_answers",
    )
    finding = models.ForeignKey(
        DiagnosticFinding,
        on_delete=models.CASCADE,
        related_name="student_diagnostic_answers",
    )
    selected_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "finding"],
                name="uq_diagnostic_case_finding_answer",
            )
        ]

    def __str__(self):
        return f"{self.session} — {self.finding.title}: {self.selected_count}"


class CellSimilarity(models.Model):
    source_cell = models.ForeignKey(
        Cell,
        on_delete=models.CASCADE,
        related_name="similar_cells_from",
    )
    target_cell = models.ForeignKey(
        Cell,
        on_delete=models.CASCADE,
        related_name="similar_cells_to",
    )
    weight = models.FloatField(default=1.0)

    class Meta:
        unique_together = ("source_cell", "target_cell")
        verbose_name = "Похожесть клеток"
        verbose_name_plural = "Похожесть клеток"

    def __str__(self):
        return f"{self.source_cell} → {self.target_cell} ({self.weight})"