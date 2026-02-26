import random

from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from .models import CellImage


# Простая сессия теста
TEST_LENGTH = 10


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
def start_test(request, mode):
    request.session["mode"] = mode
    request.session["current"] = 0
    request.session["score"] = 0
    request.session["used_images"] = []

    return render(request, "test.html")


@login_required
def get_question(request):
    current = request.session.get("current", 0)
    used = request.session.get("used_images", [])

    if current >= TEST_LENGTH:
        return render(request, "partials/result.html", {
            "score": request.session.get("score", 0),
            "total": TEST_LENGTH,
            "percent": int((request.session.get("score", 0) / TEST_LENGTH) * 100),
        })

    qs = CellImage.objects.exclude(id__in=used)

    # если картинки закончились
    if not qs.exists():
        return render(request, "partials/result.html", {
            "score": request.session.get("score", 0),
            "total": current if current else TEST_LENGTH,
            "percent": int((request.session.get("score", 0) / (current if current else 1)) * 100),
        })

    image = qs.order_by("?").first()  # <-- вместо random.choice()

    used.append(image.id)
    request.session["used_images"] = used

    percent = int((current / TEST_LENGTH) * 100)

    return render(request, "partials/question.html", {
        "image": image,
        "current": current + 1,
        "total": TEST_LENGTH,
        "percent": percent,
    })


@login_required
def submit_answer(request):
    image_id = request.POST.get("image_id")
    answer = request.POST.get("answer")

    image = CellImage.objects.get(id=image_id)

    if answer.strip().lower() == image.cell.name.lower():
        request.session["score"] += 1

    request.session["current"] += 1

    return get_question(request)


@login_required
def test_result(request):
    score = request.session.get("score", 0)

    context = {
        "score": score,
        "total": TEST_LENGTH,
        "percent": int((score / TEST_LENGTH) * 100)
    }

    return render(request, "partials/result.html", context)