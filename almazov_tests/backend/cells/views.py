from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import F
from .models import CellImage

TEST_LENGTH = 10


def _pick_random_images_ids(limit: int):
    # случайная выборка
    return list(CellImage.objects.order_by("?").values_list("id", flat=True)[:limit])


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
def start_test(request, mode: str):
    """
    mode: 'random' или 'trainer'
    """
    request.session["mode"] = mode
    request.session["current"] = 0
    request.session["score"] = 0

    # В random мы заранее формируем список изображений
    # (trainer позже заменим на адаптивный подбор)
    if mode == "random":
        ids = _pick_random_images_ids(TEST_LENGTH)
    else:
        # пока заглушка: тоже случайные
        # на следующем шаге подключим твой улучшенный алгоритм trainer
        ids = _pick_random_images_ids(TEST_LENGTH)

    request.session["test_images"] = ids
    return render(request, "test.html")


@login_required
def get_question(request):
    ids = request.session.get("test_images", [])
    current = request.session.get("current", 0)

    if not ids:
        # если тест не инициализирован, покажем dashboard
        return render(request, "partials/result.html", {
            "score": 0, "total": 0, "percent": 0
        })

    if current >= len(ids):
        score = request.session.get("score", 0)
        total = len(ids)
        percent = int((score / total) * 100) if total else 0
        return render(request, "partials/result.html", {
            "score": score, "total": total, "percent": percent
        })

    image = CellImage.objects.select_related("cell").get(id=ids[current])

    percent = int((current / len(ids)) * 100)

    return render(request, "partials/question.html", {
        "image": image,
        "current": current + 1,
        "total": len(ids),
        "percent": percent,
    })


@login_required
def submit_answer(request):
    image_id = int(request.POST.get("image_id"))
    answer = (request.POST.get("answer") or "").strip().lower()

    # текущий индекс до увеличения
    current = request.session.get("current", 0)
    ids = request.session.get("test_images", [])

    # защита от кривых сессий
    if current >= len(ids):
        return get_question(request)

    image = CellImage.objects.select_related("cell").get(id=image_id)

    correct_name = image.cell.name.strip().lower()
    is_correct = answer == correct_name

    if is_correct:
        request.session["score"] = request.session.get("score", 0) + 1

    request.session["current"] = current + 1

    # отдаём следующий вопрос, но добавим короткий feedback
    resp = get_question(request)
    # если следующий вопрос ещё есть — покажем фидбек (опционально)
    # проще всего передать через контекст, но сейчас resp уже готов.
    # Поэтому фидбек лучше показывать отдельным блоком или модалкой.
    return resp


@login_required
def test_result(request):
    return get_question(request)