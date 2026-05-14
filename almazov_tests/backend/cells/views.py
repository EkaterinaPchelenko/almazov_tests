import json
import random

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    Cell,
    CellImage,
    GlobalImageStats,
    Level,
    TestSession,
    UserImageAnswer,
    UserImagePerformance,
    DiagnosticCaseSession,
)
from .services.level_tests import (
    build_level_overview,
    create_level_session,
    ensure_level_progress_for_user,
    finalize_level_session,
    get_allowed_cell_ids_for_level,
    get_choice_count_for_progress,
    get_or_create_level_progress,
)
from .services.diagnostic_cases import (
    build_counts_comparison,
    create_diagnostic_case_session,
    finish_diagnostic_case_session,
    get_all_cell_options,
    get_available_diagnoses,
    get_current_case_batch,
    save_case_batch_answers,
)
from .services.progress import save_answer
from .services.question_builder import build_question
from .services.random_test import generate_random_images
from .services.trainer_test import generate_trainer_images


TEST_LENGTH = 10
DEFAULT_CHOICE_COUNT = 4


def _build_answer_options(
    current_item,
    choice_count=DEFAULT_CHOICE_COUNT,
    allowed_cell_ids=None,
):
    correct_name = current_item.image.cell.name

    distractor_qs = Cell.objects.exclude(id=current_item.image.cell_id)

    if allowed_cell_ids:
        distractor_qs = distractor_qs.filter(id__in=allowed_cell_ids)

    distractors = list(distractor_qs.values_list("name", flat=True).distinct())
    random.shuffle(distractors)

    options = [correct_name, *distractors[: max(choice_count - 1, 0)]]
    random.shuffle(options)

    return options


def _render_result(request, session):
    percent_result = (
        int((session.correct_answers / session.total_questions) * 100)
        if session.total_questions
        else 0
    )

    return render(
        request,
        "partials/result.html",
        {
            "session": session,
            "score": session.correct_answers,
            "total": session.total_questions,
            "percent": percent_result,
        },
    )


def _is_level_matching_session(session):
    return (
        session.mode == TestSession.Mode.LEVEL
        and session.level is not None
        and session.level.question_type == Level.QuestionType.MATCHING
    )


def _update_image_statistics(user, image, is_correct):
    performance, _ = UserImagePerformance.objects.get_or_create(
        user=user,
        image=image,
    )
    performance.total_attempts += 1
    performance.last_attempt_at = timezone.now()

    if is_correct:
        performance.correct_attempts += 1
    else:
        performance.wrong_attempts += 1

    performance.save()

    stats, _ = GlobalImageStats.objects.get_or_create(image=image)
    stats.total_attempts += 1

    if is_correct:
        stats.total_correct += 1

    stats.save()


def _parse_matching_answer(raw_answer):
    try:
        parsed = json.loads(raw_answer)
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return {
        str(cell_id): str(image_id)
        for cell_id, image_id in parsed.items()
        if cell_id and image_id
    }


def _save_matching_answer(request, session, current_item):
    raw_answer = request.POST.get("answer", "{}")
    response_time_ms_raw = request.POST.get("response_time_ms")
    response_time_ms = int(response_time_ms_raw) if response_time_ms_raw else None

    user_pairs = _parse_matching_answer(raw_answer)

    cells = Cell.objects.filter(id__in=user_pairs.keys()).in_bulk()
    selected_images = CellImage.objects.select_related("cell").filter(
        id__in=user_pairs.values()
    ).in_bulk()

    result_pairs = []
    correct_count = 0

    for cell_id, selected_image_id in user_pairs.items():
        cell = cells.get(int(cell_id)) if str(cell_id).isdigit() else None
        selected_image = (
            selected_images.get(int(selected_image_id))
            if str(selected_image_id).isdigit()
            else None
        )

        if not cell or not selected_image:
            continue

        is_pair_correct = selected_image.cell_id == cell.id

        if is_pair_correct:
            correct_count += 1

        result_pairs.append(
            {
                "cell": cell,
                "selected_image": selected_image,
                "correct_image": selected_image
                if is_pair_correct
                else cell.cell_images.first(),
                "is_correct": is_pair_correct,
            }
        )

    total = len(result_pairs)
    percent = int((correct_count / total) * 100) if total else 0
    is_question_correct = total > 0 and correct_count == total

    answer = UserImageAnswer.objects.create(
        session=session,
        session_image=current_item,
        image=current_item.image,
        order_number=current_item.order_number,
        user_answer=raw_answer,
        normalized_answer=raw_answer,
        is_correct=is_question_correct,
        response_time_ms=response_time_ms,
    )

    current_item.is_answered = True
    current_item.save(update_fields=["is_answered"])

    if is_question_correct:
        session.correct_answers += 1

    has_remaining_questions = session.session_images.filter(is_answered=False).exists()

    if not has_remaining_questions:
        session.status = TestSession.Status.COMPLETED
        session.finished_at = timezone.now()

    session.save(update_fields=["correct_answers", "status", "finished_at"])

    _update_image_statistics(
        user=session.user,
        image=current_item.image,
        is_correct=is_question_correct,
    )

    session.refresh_from_db()

    if session.status == TestSession.Status.COMPLETED:
        finalize_level_session(session)
        session.refresh_from_db()

    return render(
        request,
        "partials/test_question.html",
        {
            "session": session,
            "question": {"type": "matching"},
            "order_number": current_item.order_number,
            "total": session.total_questions,
            "percent": int((current_item.order_number / session.total_questions) * 100)
            if session.total_questions
            else 0,
            "show_results": True,
            "pairs": result_pairs,
            "correct": correct_count,
            "total_pairs": total,
            "matching_percent": percent,
            "answer": answer,
        },
    )


@login_required
def dashboard(request):
    ensure_level_progress_for_user(request.user)

    completed_sessions = TestSession.objects.filter(
        user=request.user,
        status=TestSession.Status.COMPLETED,
    ).order_by("-started_at")

    total_answers = UserImageAnswer.objects.filter(session__user=request.user).count()

    correct_answers = UserImageAnswer.objects.filter(
        session__user=request.user,
        is_correct=True,
    ).count()

    average_accuracy = int((correct_answers / total_answers) * 100) if total_answers else 0
    recent_sessions = completed_sessions[:4]
    tests_completed = completed_sessions.count()

    performances = UserImagePerformance.objects.filter(user=request.user)

    mastered_count = 0
    in_progress_count = 0
    revision_count = 0

    for perf in performances:
        if perf.total_attempts >= 3 and perf.error_rate <= 0.2:
            mastered_count += 1
        elif perf.total_attempts >= 2 and perf.error_rate >= 0.5:
            revision_count += 1
        elif perf.total_attempts > 0:
            in_progress_count += 1

    level_overview = build_level_overview(request.user)

    context = {
        "average_accuracy": average_accuracy,
        "tests_completed": tests_completed,
        "recent_sessions": recent_sessions,
        "mastered_count": mastered_count,
        "in_progress_count": in_progress_count,
        "revision_count": revision_count,
        "level_overview": level_overview,
        "study_streak_days": 7,
    }

    return render(request, "dashboard.html", context)


@login_required
def levels_page(request):
    context = build_level_overview(request.user)
    return render(request, "levels.html", context)


@login_required
def start_test(request, mode):
    if mode not in {TestSession.Mode.RANDOM, TestSession.Mode.TRAINER}:
        return redirect("dashboard")

    session = TestSession.objects.create(
        user=request.user,
        mode=mode,
        total_questions=TEST_LENGTH,
        status=TestSession.Status.IN_PROGRESS,
    )

    if mode == TestSession.Mode.RANDOM:
        selected = generate_random_images(TEST_LENGTH)
    else:
        selected = generate_trainer_images(request.user, TEST_LENGTH)

    session_images = []

    for idx, item in enumerate(selected, start=1):
        if isinstance(item, tuple):
            image, source, score = item
        else:
            image, source, score = item, "random", 0.0

        session_images.append(
            session.session_images.model(
                session=session,
                image=image,
                order_number=idx,
                source=source,
                score_snapshot=score,
            )
        )

    session.session_images.model.objects.bulk_create(session_images)

    return redirect("test_page", session_id=session.id)


@login_required
def start_level_test(request, level_id):
    level = get_object_or_404(Level, id=level_id, is_active=True)
    progress = get_or_create_level_progress(request.user, level)

    if not progress.is_unlocked:
        return redirect("levels_page")

    try:
        session = create_level_session(request.user, level)
    except ValueError:
        return redirect("levels_page")

    return redirect("test_page", session_id=session.id)


@login_required
def test_page(request, session_id):
    session = get_object_or_404(TestSession, id=session_id, user=request.user)
    return render(request, "test.html", {"session": session})


@login_required
def test_question_partial(request, session_id):
    session = get_object_or_404(
        TestSession.objects.prefetch_related("session_images__image__cell"),
        id=session_id,
        user=request.user,
    )

    current_item = session.session_images.filter(is_answered=False).first()

    if not current_item:
        if session.status != TestSession.Status.COMPLETED:
            session.status = TestSession.Status.COMPLETED
            session.finished_at = timezone.now()
            session.save(update_fields=["status", "finished_at"])

        return _render_result(request, session)

    percent = int(((current_item.order_number - 1) / session.total_questions) * 100)

    choice_count = DEFAULT_CHOICE_COUNT
    allowed_cell_ids = None

    if session.mode == TestSession.Mode.LEVEL and session.level:
        progress = get_or_create_level_progress(request.user, session.level)
        choice_count = get_choice_count_for_progress(progress)
        allowed_cell_ids = get_allowed_cell_ids_for_level(session.level)

    question = build_question(
        current_item=current_item,
        session=session,
        choice_count=choice_count,
        allowed_cell_ids=allowed_cell_ids,
    )

    return render(
        request,
        "partials/test_question.html",
        {
            "session": session,
            "question": question,
            "order_number": current_item.order_number,
            "total": session.total_questions,
            "percent": percent,
            "choice_count": choice_count,
        },
    )


@login_required
def submit_answer_htmx(request, session_id):
    if request.method != "POST":
        return redirect("test_page", session_id=session_id)

    session = get_object_or_404(
        TestSession.objects.prefetch_related("session_images__image__cell"),
        id=session_id,
        user=request.user,
    )

    current_item = session.session_images.filter(is_answered=False).first()

    if not current_item:
        return _render_result(request, session)

    if (
        session.mode == TestSession.Mode.LEVEL
        and session.level is not None
        and session.level.question_type == Level.QuestionType.MATCHING
    ):

        raw_answer = request.POST.get("answer", "{}")
        print("POST DATA:", request.POST)
        print("RAW MATCHING ANSWER:", raw_answer)
        try:
            user_pairs = json.loads(raw_answer)
        except json.JSONDecodeError:
            user_pairs = {}

        result_pairs = []
        correct_count = 0

        for cell_id, selected_image_id in user_pairs.items():

            cell = get_object_or_404(Cell, id=cell_id)
            selected_image = get_object_or_404(
                CellImage.objects.select_related("cell"),
                id=selected_image_id,
            )
            print(selected_image.cell_id, cell.id)
            is_correct = selected_image.cell_id == cell.id

            if is_correct:
                correct_count += 1

            result_pairs.append(
                {
                    "cell": cell,
                    "selected_image": selected_image,
                    "is_correct": is_correct,
                }
            )

        total = len(result_pairs)
        percent = int((correct_count / total) * 100) if total else 0
        is_question_correct = total > 0 and correct_count == total

        UserImageAnswer.objects.create(
            session=session,
            session_image=current_item,
            image=current_item.image,
            order_number=current_item.order_number,
            user_answer=raw_answer,
            normalized_answer=raw_answer,
            is_correct=is_question_correct,
        )

        current_item.is_answered = True
        current_item.save(update_fields=["is_answered"])

        if is_question_correct:
            session.correct_answers += 1

        has_remaining_questions = session.session_images.filter(
            is_answered=False
        ).exists()

        if not has_remaining_questions:
            session.status = TestSession.Status.COMPLETED
            session.finished_at = timezone.now()

        session.save(update_fields=["correct_answers", "status", "finished_at"])

        if session.status == TestSession.Status.COMPLETED:
            finalize_level_session(session)
            session.refresh_from_db()

        question = {
            "type": "matching",
        }

        return render(
            request,
            "partials/test_question.html",
            {
                "session": session,
                "question": question,
                "order_number": current_item.order_number,
                "total": session.total_questions,
                "percent": int(
                    (current_item.order_number / session.total_questions) * 100
                )
                if session.total_questions
                else 0,
                "show_matching_result": True,
                "matching_pairs": result_pairs,
                "matching_correct": correct_count,
                "matching_total": total,
                "matching_percent": percent,
            },
        )

    user_answer = request.POST.get("answer", "")

    response_time_ms_raw = request.POST.get("response_time_ms")
    response_time_ms = int(response_time_ms_raw) if response_time_ms_raw else None

    answer = save_answer(
        session=session,
        session_image=current_item,
        user_answer=user_answer,
        response_time_ms=response_time_ms,
    )

    selected_image = None

    if (
            session.mode == TestSession.Mode.LEVEL
            and session.level
            and session.level.question_type == Level.QuestionType.NAME_TO_IMAGE
    ):
        selected_image = CellImage.objects.filter(id=user_answer).first()

    session.refresh_from_db()

    if (
        session.status == TestSession.Status.COMPLETED
        and session.mode == TestSession.Mode.LEVEL
    ):
        finalize_level_session(session)
        session.refresh_from_db()

    return render(
        request,
        "partials/answer_feedback.html",
        {
            "session": session,
            "answer": answer,
            "selected_image": selected_image,
        },
    )

@login_required
def start_diagnostic_case_level(request):
    session = create_diagnostic_case_session(request.user)

    if session is None:
        return render(
            request,
            "diagnostic_cases/all_completed.html",
            {},
        )

    return redirect("diagnostic_case_page", session_id=session.id)


@login_required
def diagnostic_case_page(request, session_id):
    session = get_object_or_404(
        DiagnosticCaseSession.objects.select_related("case"),
        id=session_id,
        user=request.user,
    )

    return render(
        request,
        "diagnostic_cases/case_page.html",
        {
            "session": session,
        },
    )


@login_required
def diagnostic_case_batch_partial(request, session_id):
    session = get_object_or_404(
        DiagnosticCaseSession.objects.select_related("case"),
        id=session_id,
        user=request.user,
    )

    if session.status == DiagnosticCaseSession.Status.AWAITING_DIAGNOSIS:
        return render(
            request,
            "diagnostic_cases/partials/case_counts.html",
            {
                "session": session,
                "comparison": build_counts_comparison(session),
                "diagnoses": get_available_diagnoses(),
            },
        )

    if session.status == DiagnosticCaseSession.Status.COMPLETED:
        return render(
            request,
            "diagnostic_cases/partials/case_result.html",
            {
                "session": session,
                "comparison": build_counts_comparison(session),
            },
        )

    batch_images = get_current_case_batch(session)
    cell_options = get_all_cell_options()

    total_images = session.case.case_images.count()
    progress_percent = int((session.current_offset / total_images) * 100) if total_images else 0

    return render(
        request,
        "diagnostic_cases/partials/case_batch.html",
        {
            "session": session,
            "batch_images": batch_images,
            "cell_options": cell_options,
            "progress_percent": progress_percent,
            "from_number": session.current_offset + 1,
            "to_number": min(session.current_offset + session.batch_size, total_images),
            "total_images": total_images,
        },
    )


@login_required
def submit_diagnostic_case_batch(request, session_id):
    if request.method != "POST":
        return redirect("diagnostic_case_page", session_id=session_id)

    session = get_object_or_404(
        DiagnosticCaseSession.objects.select_related("case"),
        id=session_id,
        user=request.user,
    )

    raw_answer = {
        key.replace("cell_", ""): value
        for key, value in request.POST.items()
        if key.startswith("cell_")
    }

    session, error_message = save_case_batch_answers(session, raw_answer)

    if error_message:
        batch_images = get_current_case_batch(session)
        cell_options = get_all_cell_options()
        total_images = session.case.case_images.count()
        progress_percent = int((session.current_offset / total_images) * 100) if total_images else 0

        return render(
            request,
            "diagnostic_cases/partials/case_batch.html",
            {
                "session": session,
                "batch_images": batch_images,
                "cell_options": cell_options,
                "progress_percent": progress_percent,
                "from_number": session.current_offset + 1,
                "to_number": min(session.current_offset + session.batch_size, total_images),
                "total_images": total_images,
                "error_message": error_message,
            },
        )

    if session.status == DiagnosticCaseSession.Status.AWAITING_DIAGNOSIS:
        return render(
            request,
            "diagnostic_cases/partials/case_counts.html",
            {
                "session": session,
                "comparison": build_counts_comparison(session),
                "diagnoses": get_available_diagnoses(),
            },
        )

    return diagnostic_case_batch_partial(request, session.id)


@login_required
def submit_diagnostic_case_diagnosis(request, session_id):
    if request.method != "POST":
        return redirect("diagnostic_case_page", session_id=session_id)

    session = get_object_or_404(
        DiagnosticCaseSession.objects.select_related("case"),
        id=session_id,
        user=request.user,
    )

    selected_diagnosis = request.POST.get("diagnosis", "")
    session = finish_diagnostic_case_session(session, selected_diagnosis)

    return render(
        request,
        "diagnostic_cases/partials/case_result.html",
        {
            "session": session,
            "comparison": build_counts_comparison(session),
        },
    )