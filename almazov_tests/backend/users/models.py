from django.db import models

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.STUDENT
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class StudentGroup(models.Model):
    number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер группы",
    )

    class Meta:
        ordering = ["number"]
        verbose_name = "Группа студентов"
        verbose_name_plural = "Группы студентов"

    def __str__(self):
        return self.number


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    group = models.ForeignKey(
        StudentGroup,
        on_delete=models.PROTECT,
        related_name="students",
        verbose_name="Группа",
    )
    overall_accuracy = models.FloatField(default=0)
    total_tests_passed = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.email} profile"