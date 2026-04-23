import random

from django.db import transaction
from django.utils import timezone

from cells.models import (
    CellImage,
    Level,
    TestSession,
    TestSessionImage,
    UserLevelProgress,
)


def ensure_level_progress_for_user(user):
    levels = Level.objects.filter(is_active=True).order_by("order")
    first_level = levels.first()
    if not first_level:
        return

    for level in levels:
        progress, created = UserLevelProgress.objects.get_or_create(
            user=user,
            level=level,
            defaults={
                "is_unlocked": level == first_level,
                "unlocked_at": timezone.now() if level == first_level else None,
            },
        )
        if created:
            continue

        if level == first_level and not progress.is_unlocked:
            progress.is_unlocked = True
            progress.unlocked_at = timezone.now()
            progress.save(update_fields=["is_unlocked", "unlocked_at"])


def get_or_create_level_progress(user, level):
    ensure_level_progress_for_user(user)
    progress, _ = UserLevelProgress.objects.get_or_create(
        user=user,
        level=level,
        defaults={
            "is_unlocked": level.order == 1,
            "unlocked_at": timezone.now() if level.order == 1 else None,
        },
    )
    return progress


def get_choice_count_for_progress(progress):
    return min(2 + progress.completions_count, 6)


def get_next_level(level):
    return (
        Level.objects.filter(is_active=True, order__gt=level.order)
        .order_by("order")
        .first()
    )


def unlock_next_level_for_user(user, current_level):
    next_level = get_next_level(current_level)
    if not next_level:
        return None

    progress, _ = UserLevelProgress.objects.get_or_create(
        user=user,
        level=next_level,
        defaults={
            "is_unlocked": True,
            "unlocked_at": timezone.now(),
        },
    )

    if not progress.is_unlocked:
        progress.is_unlocked = True
        progress.unlocked_at = timezone.now()
        progress.save(update_fields=["is_unlocked", "unlocked_at"])

    return progress


def get_allowed_cell_ids_for_level(level):
    return list(
        level.level_cells.values_list("cell_id", flat=True)
    )


def generate_level_images(level, question_count=None):
    cell_ids = get_allowed_cell_ids_for_level(level)
    if not cell_ids:
        return []

    if question_count is None:
        question_count = level.question_count

    images = list(
        CellImage.objects.select_related("cell")
        .filter(cell_id__in=cell_ids)
    )

    random.shuffle(images)
    return images[:question_count]


@transaction.atomic
def create_level_session(user, level):
    progress = get_or_create_level_progress(user, level)

    if not progress.is_unlocked:
        raise ValueError("Level is locked")

    selected_images = generate_level_images(level, level.question_count)
    if not selected_images:
        raise ValueError("No images found for this level")

    session = TestSession.objects.create(
        user=user,
        mode=TestSession.Mode.LEVEL,
        status=TestSession.Status.IN_PROGRESS,
        total_questions=len(selected_images),
        level=level,
        level_attempt_number=progress.completions_count + 1,
    )

    session_items = [
        TestSessionImage(
            session=session,
            image=image,
            order_number=index,
            source=TestSessionImage.Source.LEVEL,
            score_snapshot=0.0,
        )
        for index, image in enumerate(selected_images, start=1)
    ]
    TestSessionImage.objects.bulk_create(session_items)

    return session


@transaction.atomic
def finalize_level_session(session):
    if session.mode != TestSession.Mode.LEVEL or not session.level:
        return None

    progress = get_or_create_level_progress(session.user, session.level)

    progress.completions_count += 1
    progress.last_score = session.correct_answers
    progress.best_score = max(progress.best_score, session.correct_answers)

    if progress.is_completed and progress.completed_at is None:
        progress.completed_at = timezone.now()

    progress.save(
        update_fields=[
            "completions_count",
            "last_score",
            "best_score",
            "completed_at",
        ]
    )

    if progress.is_completed:
        unlock_next_level_for_user(session.user, session.level)

    return progress


def build_level_overview(user):
    ensure_level_progress_for_user(user)

    levels = (
        Level.objects.filter(is_active=True)
        .prefetch_related("level_cells")
        .order_by("order")
    )

    progress_map = {
        progress.level_id: progress
        for progress in UserLevelProgress.objects.filter(user=user).select_related("level")
    }

    items = []
    unlocked_count = 0

    for level in levels:
        progress = progress_map.get(level.id)
        if progress and progress.is_unlocked:
            unlocked_count += 1

        items.append(
            {
                "level": level,
                "progress": progress,
                "is_unlocked": bool(progress and progress.is_unlocked),
                "is_completed": bool(progress and progress.is_completed),
                "completion_percent": progress.completion_percent if progress else 0,
                "completions_count": progress.completions_count if progress else 0,
                "choice_count": get_choice_count_for_progress(progress) if progress else 2,
            }
        )

    total_levels = levels.count()
    total_completions = sum(item["completions_count"] for item in items)
    total_required = sum(item["level"].required_completions for item in items) or 1

    return {
        "levels": items,
        "unlocked_count": unlocked_count,
        "total_levels": total_levels,
        "total_completions": total_completions,
        "total_required": total_required,
        "overall_percent": int((total_completions / total_required) * 100),
    }