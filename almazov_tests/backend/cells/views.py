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

    if current >= TEST_LENGTH:
        return render(request, "partials/result.html")

    used = request.session.get("used_images", [])

    images = CellImage.objects.exclude(id__in=used)
    image = random.choice(images)

    used.append(image.id)
    request.session["used_images"] = used

    percent = int((current / TEST_LENGTH) * 100)

    context = {
        "image": image,
        "current": current + 1,
        "total": TEST_LENGTH,
        "percent": percent,
    }

    return render(request, "partials/question.html", context)


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