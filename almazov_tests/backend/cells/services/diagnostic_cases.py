import json

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from cells.models import (Cell,
    DiagnosticCase,
    DiagnosticCaseExpectedCount,
    DiagnosticCaseImage,
    DiagnosticCaseImageAnswer,
    DiagnosticCaseProgress,
    DiagnosticCaseSession,
)


BATCH_SIZE = 5


def get_next_diagnostic_case_for_user(user):
    failed_progress = (
        DiagnosticCaseProgress.objects
        .filter(
            user=user,
            is_completed=False,
            attempts_count__gt=0,
            case__is_active=True,
        )
        .select_related("case")
        .order_by("-last_attempt_at")
        .first()
    )

    if failed_progress:
        return failed_progress.case

    completed_case_ids = DiagnosticCaseProgress.objects.filter(
        user=user,
        is_completed=True,
    ).values_list("case_id", flat=True)

    return (
        DiagnosticCase.objects
        .filter(is_active=True)
        .exclude(id__in=completed_case_ids)
        .order_by("?")
        .first()
    )


@transaction.atomic
def create_diagnostic_case_session(user):
    case = get_next_diagnostic_case_for_user(user)

    if case is None:
        return None

    progress, _ = DiagnosticCaseProgress.objects.get_or_create(
        user=user,
        case=case,
    )

    progress.attempts_count += 1
    progress.last_attempt_at = timezone.now()
    progress.save(update_fields=["attempts_count", "last_attempt_at"])

    session = DiagnosticCaseSession.objects.create(
        user=user,
        case=case,
        status=DiagnosticCaseSession.Status.IN_PROGRESS,
        current_offset=0,
        batch_size=BATCH_SIZE,
    )

    return session


def get_current_case_batch(session):
    return (
        DiagnosticCaseImage.objects
        .filter(case=session.case)
        .order_by("order_number", "id")
        [session.current_offset: session.current_offset + session.batch_size]
    )


def get_all_cell_options():
    return Cell.objects.order_by("name")


def parse_batch_answers(raw_answer):
    if not raw_answer:
        return {}

    try:
        parsed = json.loads(raw_answer)
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return {
        int(case_image_id): int(cell_id)
        for case_image_id, cell_id in parsed.items()
        if str(case_image_id).isdigit() and str(cell_id).isdigit()
    }


@transaction.atomic
def save_case_batch_answers(session, raw_answer):
    answers = parse_batch_answers(raw_answer)

    current_images = list(get_current_case_batch(session))
    current_image_ids = {image.id for image in current_images}

    for case_image_id, selected_cell_id in answers.items():
        if case_image_id not in current_image_ids:
            continue

        DiagnosticCaseImageAnswer.objects.update_or_create(
            session=session,
            case_image_id=case_image_id,
            defaults={
                "selected_cell_id": selected_cell_id,
            },
        )

    session.current_offset += session.batch_size

    total_images = DiagnosticCaseImage.objects.filter(case=session.case).count()

    if session.current_offset >= total_images:
        session.status = DiagnosticCaseSession.Status.AWAITING_DIAGNOSIS

    session.save(update_fields=["current_offset", "status"])

    return session


def get_student_cell_counts(session):
    rows = (
        DiagnosticCaseImageAnswer.objects
        .filter(session=session)
        .values("selected_cell_id", "selected_cell__name")
        .annotate(count=Count("id"))
        .order_by("selected_cell__name")
    )

    return {
        row["selected_cell_id"]: {
            "cell_name": row["selected_cell__name"],
            "count": row["count"],
        }
        for row in rows
    }


def get_expected_cell_counts(case):
    rows = (
        DiagnosticCaseExpectedCount.objects
        .filter(case=case)
        .select_related("cell")
        .order_by("cell__name")
    )

    return {
        row.cell_id: {
            "cell_name": row.cell.name,
            "count": row.count,
        }
        for row in rows
    }


def build_counts_comparison(session):
    student_counts = get_student_cell_counts(session)
    expected_counts = get_expected_cell_counts(session.case)

    all_cell_ids = set(student_counts.keys()) | set(expected_counts.keys())

    comparison = []

    for cell_id in all_cell_ids:
        student_item = student_counts.get(cell_id)
        expected_item = expected_counts.get(cell_id)

        cell_name = (
            expected_item["cell_name"]
            if expected_item
            else student_item["cell_name"]
        )

        student_count = student_item["count"] if student_item else 0
        expected_count = expected_item["count"] if expected_item else 0

        comparison.append(
            {
                "cell_id": cell_id,
                "cell_name": cell_name,
                "student_count": student_count,
                "expected_count": expected_count,
                "is_correct": student_count == expected_count,
            }
        )

    return sorted(comparison, key=lambda item: item["cell_name"])


def counts_are_correct(session):
    comparison = build_counts_comparison(session)
    return all(item["is_correct"] for item in comparison)


def get_available_diagnoses():
    return (
        DiagnosticCase.objects
        .filter(is_active=True)
        .exclude(diagnosis="")
        .values_list("diagnosis", flat=True)
        .distinct()
        .order_by("diagnosis")
    )


@transaction.atomic
def finish_diagnostic_case_session(session, selected_diagnosis):
    selected_diagnosis = selected_diagnosis.strip()

    session.selected_diagnosis = selected_diagnosis
    session.counts_are_correct = counts_are_correct(session)
    session.diagnosis_is_correct = selected_diagnosis == session.case.diagnosis
    session.status = DiagnosticCaseSession.Status.COMPLETED
    session.finished_at = timezone.now()

    session.save(
        update_fields=[
            "selected_diagnosis",
            "counts_are_correct",
            "diagnosis_is_correct",
            "status",
            "finished_at",
        ]
    )

    progress, _ = DiagnosticCaseProgress.objects.get_or_create(
        user=session.user,
        case=session.case,
    )

    if session.counts_are_correct:
        progress.is_completed = True
        progress.completed_at = timezone.now()
    else:
        progress.is_completed = False
        progress.completed_at = None

    progress.last_attempt_at = timezone.now()
    progress.save(
        update_fields=[
            "is_completed",
            "completed_at",
            "last_attempt_at",
        ]
    )

    return session