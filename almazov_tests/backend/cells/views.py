from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import TestSession
from .services.progress import save_answer
from .services.random_test import generate_random_images
from .services.trainer_test import generate_trainer_images

TEST_LENGTH = 10


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


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

        return render(
            request,
            "partials/result.html",
            {
                "session": session,
                "score": session.correct_answers,
                "total": session.total_questions,
                "percent": int((session.correct_answers / session.total_questions) * 100)
                if session.total_questions else 0,
            },
        )

    percent = int(((current_item.order_number - 1) / session.total_questions) * 100)

    return render(
        request,
        "partials/test_question.html",
        {
            "session": session,
            "image": current_item.image,
            "order_number": current_item.order_number,
            "total": session.total_questions,
            "percent": percent,
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
        return render(
            request,
            "partials/result.html",
            {
                "session": session,
                "score": session.correct_answers,
                "total": session.total_questions,
                "percent": int((session.correct_answers / session.total_questions) * 100)
                if session.total_questions else 0,
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

    return render(
        request,
        "partials/answer_feedback.html",
        {
            "session": session,
            "answer": answer,
        },
    )