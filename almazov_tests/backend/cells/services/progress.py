from django.db import transaction
from django.utils import timezone
import json

from cells.models import (
    GlobalImageStats,
    TestSession,
    TestSessionImage,
    UserImageAnswer,
    UserImagePerformance,
)


def normalize_text(value: str) -> str:
    return value.strip().lower()


@transaction.atomic
def save_answer(session, session_image, user_answer, response_time_ms=None):

    if session.status != TestSession.Status.IN_PROGRESS:
        return None

    question_type = None
    if session.mode == TestSession.Mode.LEVEL and session.level:
        question_type = session.level.question_type

    is_correct = False
    normalized_answer = str(user_answer)

    if question_type in [None, "image_to_name"]:
        correct = normalize_text(session_image.image.cell.name)
        normalized_answer = normalize_text(user_answer)
        is_correct = normalized_answer == correct

    elif question_type == "name_to_image":
        correct = str(session_image.image.id)
        is_correct = str(user_answer) == correct

    elif question_type == "matching":
        try:
            user_pairs = json.loads(user_answer)
        except Exception:
            user_pairs = {}

        correct_pairs = {}

        # правильные соответствия
        for pair in session.session_images.filter(order_number=session_image.order_number):
            correct_pairs[str(pair.image.cell.id)] = str(pair.image.id)

        # считаем правильные
        correct_count = 0
        total = len(user_pairs)

        for cell_id, image_id in user_pairs.items():
            if correct_pairs.get(cell_id) == image_id:
                correct_count += 1

        # считаем процент
        is_correct = correct_count == total and total > 0

    answer = UserImageAnswer.objects.create(
        session=session,
        session_image=session_image,
        image=session_image.image,
        order_number=session_image.order_number,
        user_answer=str(user_answer),
        normalized_answer=normalized_answer,
        is_correct=is_correct,
        response_time_ms=response_time_ms,
    )

    session_image.is_answered = True
    session_image.save(update_fields=["is_answered"])

    if is_correct:
        session.correct_answers += 1

    remaining = session.session_images.filter(is_answered=False).exists()

    if not remaining:
        session.status = TestSession.Status.COMPLETED
        session.finished_at = timezone.now()

    session.save(update_fields=["correct_answers", "status", "finished_at"])

    perf, _ = UserImagePerformance.objects.get_or_create(
        user=session.user,
        image=session_image.image,
    )

    perf.total_attempts += 1
    perf.last_attempt_at = timezone.now()

    if is_correct:
        perf.correct_attempts += 1
    else:
        perf.wrong_attempts += 1

    perf.save()

    stats, _ = GlobalImageStats.objects.get_or_create(
        image=session_image.image
    )

    stats.total_attempts += 1
    if is_correct:
        stats.total_correct += 1

    stats.save()

    return answer