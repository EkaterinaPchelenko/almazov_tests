import math
import random
from collections import defaultdict

from cells.models import (
    CellImage,
    ImageSimilarity,
    TestSessionImage,
    UserImagePerformance,
)

ALPHA = 1.0


def smoothed_error_rate(correct_attempts: int, total_attempts: int) -> float:
    return 1.0 - ((correct_attempts + ALPHA) / (total_attempts + 2 * ALPHA))


def novelty_score(total_attempts: int) -> float:
    return 1.0 if total_attempts == 0 else math.exp(-total_attempts)


def get_personal_error_scores(user) -> dict[int, float]:
    performances = UserImagePerformance.objects.filter(user=user).only(
        "image_id",
        "correct_attempts",
        "total_attempts",
    )

    result = {}
    for perf in performances:
        result[perf.image_id] = smoothed_error_rate(
            perf.correct_attempts,
            perf.total_attempts,
        )
    return result


def get_problem_images(user, min_attempts: int = 1, min_error: float = 0.4) -> list[int]:
    performances = UserImagePerformance.objects.filter(
        user=user,
        total_attempts__gte=min_attempts,
    )

    result = []
    for perf in performances:
        error = smoothed_error_rate(perf.correct_attempts, perf.total_attempts)
        if error >= min_error:
            result.append(perf.image_id)
    return result


def get_similarity_scores(problem_image_ids: list[int]) -> dict[int, float]:
    if not problem_image_ids:
        return {}

    similarity_rows = ImageSimilarity.objects.filter(
        image_from_id__in=problem_image_ids
    ).select_related("image_to")

    scores = defaultdict(float)
    for row in similarity_rows:
        scores[row.image_to_id] += row.similarity_score

    return dict(scores)


def generate_trainer_images(user, limit: int = 10):
    personal_scores = get_personal_error_scores(user)
    problem_image_ids = get_problem_images(user)
    similarity_scores = get_similarity_scores(problem_image_ids)

    attempted_image_ids = set(
        UserImagePerformance.objects.filter(user=user).values_list("image_id", flat=True)
    )

    all_images = list(CellImage.objects.select_related("cell").all())
    scored = []

    for image in all_images:
        personal = personal_scores.get(image.id, 0.0)
        similarity = similarity_scores.get(image.id, 0.0)
        novelty = 1.0 if image.id not in attempted_image_ids else 0.0

        score = (
            0.60 * personal
            + 0.30 * similarity
            + 0.10 * novelty
        )

        if score > 0:
            source = TestSessionImage.Source.PERSONAL_ERROR if personal >= similarity else TestSessionImage.Source.SIMILAR
            if novelty == 1.0 and personal == 0 and similarity == 0:
                source = TestSessionImage.Source.NOVEL
            scored.append((image, source, score))

    scored.sort(key=lambda x: x[2], reverse=True)

    selected = scored[: max(1, int(limit * 0.8))]
    selected_ids = {item[0].id for item in selected}

    novel_pool = [
        img for img in all_images
        if img.id not in selected_ids
    ]
    random.shuffle(novel_pool)

    while len(selected) < limit and novel_pool:
        img = novel_pool.pop()
        selected.append((img, TestSessionImage.Source.NOVEL, 0.1))

    return selected[:limit]