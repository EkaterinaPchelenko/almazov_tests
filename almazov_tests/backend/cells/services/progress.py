from django.db import transaction
from django.db.models import F
from django.utils import timezone

from cells.models import (
    GlobalImageStats,
    TestSession,
    TestSessionImage,
    UserImageAnswer,
    UserImagePerformance,
)
from cells.services.answers import normalize_answer


@transaction.atomic
def save_answer(
    *,
    session: TestSession,
    session_image: TestSessionImage,
    user_answer: str,
    response_time_ms: int | None = None,
) -> UserImageAnswer:
    normalized_user_answer = normalize_answer(user_answer)
    correct_answer = normalize_answer(session_image.image.cell.name)
    is_correct = normalized_user_answer == correct_answer

    answer = UserImageAnswer.objects.create(
        session=session,
        session_image=session_image,
        image=session_image.image,
        order_number=session_image.order_number,
        user_answer=user_answer,
        normalized_answer=normalized_user_answer,
        is_correct=is_correct,
        response_time_ms=response_time_ms,
    )

    session_image.is_answered = True
    session_image.save(update_fields=["is_answered"])

    performance, _ = UserImagePerformance.objects.get_or_create(
        user=session.user,
        image=session_image.image,
        defaults={
            "total_attempts": 0,
            "correct_attempts": 0,
            "wrong_attempts": 0,
        },
    )

    performance.total_attempts = F("total_attempts") + 1
    if is_correct:
        performance.correct_attempts = F("correct_attempts") + 1
    else:
        performance.wrong_attempts = F("wrong_attempts") + 1
    performance.last_attempt_at = timezone.now()
    performance.save()

    global_stats, _ = GlobalImageStats.objects.get_or_create(
        image=session_image.image,
        defaults={
            "total_attempts": 0,
            "total_correct": 0,
        },
    )
    global_stats.total_attempts = F("total_attempts") + 1
    if is_correct:
        global_stats.total_correct = F("total_correct") + 1
    global_stats.save()

    if is_correct:
        session.correct_answers = F("correct_answers") + 1
        session.save(update_fields=["correct_answers"])

    unanswered_exists = session.session_images.filter(is_answered=False).exists()
    if not unanswered_exists:
        session.status = TestSession.Status.COMPLETED
        session.finished_at = timezone.now()
        session.save(update_fields=["status", "finished_at"])

    return answer