from django.utils import timezone

from cells.models import GlobalImageStats, UserImageAnswer, UserImagePerformance


def normalize_answer(value: str) -> str:
    return (value or "").strip().lower()


def check_answer(user_answer: str, correct_name: str) -> bool:
    return normalize_answer(user_answer) == normalize_answer(correct_name)


def save_answer(session, image, user_answer, order_number):
    normalized = normalize_answer(user_answer)
    correct_name = normalize_answer(image.cell.name)
    is_correct = normalized == correct_name

    UserImageAnswer.objects.create(
        session=session,
        image=image,
        order_number=order_number,
        user_answer=user_answer,
        normalized_answer=normalized,
        is_correct=is_correct,
    )

    perf, _ = UserImagePerformance.objects.get_or_create(
        user=session.user,
        image=image,
    )
    perf.total_attempts += 1
    perf.last_attempt_at = timezone.now()

    if is_correct:
        perf.correct_attempts += 1
    else:
        perf.wrong_attempts += 1

    perf.save()

    stats, _ = GlobalImageStats.objects.get_or_create(image=image)
    stats.total_attempts += 1
    if is_correct:
        stats.total_correct += 1
    stats.save()

    if is_correct:
        session.correct_answers += 1
        session.save(update_fields=["correct_answers"])

    return is_correct