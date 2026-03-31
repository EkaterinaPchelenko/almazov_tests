from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import CellImage, TestSession, TestSessionImage
from .services.progress import save_answer
from .services.random_test import generate_random_images
from .services.trainer_test import generate_trainer_images

TEST_LENGTH = 10


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
def start_test(request, mode):
    session = TestSession.objects.create(
        user=request.user,
        mode=mode,
        total_questions=TEST_LENGTH,
    )

    if mode == TestSession.Mode.RANDOM:
        images = generate_random_images(TEST_LENGTH)
    else:
        images = generate_trainer_images(request.user, TEST_LENGTH)

    for idx, image in enumerate(images, start=1):
        TestSessionImage.objects.create(
            session=session,
            image=image,
            order_number=idx,
        )

    return redirect("test_page", session_id=session.id)


@login_required
def test_page(request, session_id):
    session = get_object_or_404(TestSession, id=session_id, user=request.user)

    current_item = session.session_images.filter(is_answered=False).first()

    if not current_item:
        if not session.is_completed:
            session.is_completed = True
            session.finished_at = timezone.now()
            session.save(update_fields=["is_completed", "finished_at"])
        return render(request, "partials/result.html", {
            "session": session,
            "score": session.correct_answers,
            "total": session.total_questions,
            "percent": int((session.correct_answers / session.total_questions) * 100) if session.total_questions else 0,
        })

    percent = int(((current_item.order_number - 1) / session.total_questions) * 100)

    return render(request, "test.html", {
        "session": session,
        "image": current_item.image,
        "order_number": current_item.order_number,
        "total": session.total_questions,
        "percent": percent,
    })


@login_required
def submit_answer(request, session_id):
    session = get_object_or_404(TestSession, id=session_id, user=request.user)

    current_item = session.session_images.filter(is_answered=False).first()
    if not current_item:
        return redirect("test_page", session_id=session.id)

    user_answer = request.POST.get("answer", "")
    save_answer(
        session=session,
        image=current_item.image,
        user_answer=user_answer,
        order_number=current_item.order_number,
    )

    current_item.is_answered = True
    current_item.save(update_fields=["is_answered"])

    return redirect("test_page", session_id=session.id)