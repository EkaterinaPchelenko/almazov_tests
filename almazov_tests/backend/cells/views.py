import random

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Cell, Level, TestSession, UserImageAnswer, UserImagePerformance
from .services.level_tests import (
    build_level_overview,
    create_level_session,
    ensure_level_progress_for_user,
    finalize_level_session,
    get_choice_count_for_progress,
    get_or_create_level_progress,
    get_allowed_cell_ids_for_level,
)
from .services.progress import save_answer
from .services.random_test import generate_random_images
from .services.trainer_test import generate_trainer_images
from .services.question_builder import build_question

TEST_LENGTH = 10
DEFAULT_CHOICE_COUNT = 4


def _build_answer_options(current_item, choice_count=DEFAULT_CHOICE_COUNT, allowed_cell_ids=None):
    correct_name = current_item.image.cell.name

    distractor_qs = Cell.objects.exclude(id=current_item.image.cell_id)
    if allowed_cell_ids:
        distractor_qs = distractor_qs.filter(id__in=allowed_cell_ids)

    distractors = list(
        distractor_qs.values_list("name", flat=True).distinct()
    )
    random.shuffle(distractors)

    options = [correct_name, *distractors[: max(choice_count - 1, 0)]]
    random.shuffle(options)
    return options


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

    percent = int(((current_item.order_number - 1) / session.total_questions) * 100)

    choice_count = DEFAULT_CHOICE_COUNT
    allowed_cell_ids = None

    if session.mode == TestSession.Mode.LEVEL and session.level:
        progress = get_or_create_level_progress(request.user, session.level)
        choice_count = get_choice_count_for_progress(progress)
        allowed_cell_ids = get_allowed_cell_ids_for_level(session.level)

    # answer_options = _build_answer_options(
    #     current_item=current_item,
    #     choice_count=choice_count,
    #     allowed_cell_ids=allowed_cell_ids,
    # )

    question = build_question(
        current_item=current_item,
        session=session,
        choice_count=choice_count,
        allowed_cell_ids=allowed_cell_ids,
    )

    # return render(
    #     request,
    #     "partials/test_question.html",
    #     {
    #         "session": session,
    #         "image": current_item.image,
    #         "order_number": current_item.order_number,
    #         "total": session.total_questions,
    #         "percent": percent,
    #         "answer_options": answer_options,
    #         "choice_count": choice_count,
    #     },
    # )

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

    user_answer = request.POST.get("answer", "")
    response_time_ms_raw = request.POST.get("response_time_ms")
    response_time_ms = int(response_time_ms_raw) if response_time_ms_raw else None

    answer = save_answer(
        session=session,
        session_image=current_item,
        user_answer=user_answer,
        response_time_ms=response_time_ms,
    )

    session.refresh_from_db()

    if session.status == TestSession.Status.COMPLETED and session.mode == TestSession.Mode.LEVEL:
        finalize_level_session(session)
        session.refresh_from_db()


    return render(
        request,
        "partials/answer_feedback.html",
        {
            "session": session,
            "answer": answer,
        },
    )