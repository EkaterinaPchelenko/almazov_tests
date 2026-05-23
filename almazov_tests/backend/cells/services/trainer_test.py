import math
import random
from collections import defaultdict

from cells.models import (
    CellImage,
    CellSimilarity,
    TestSessionImage,
    UserImagePerformance,
)

ALPHA = 1.0


def smoothed_error_rate(correct_attempts: int, total_attempts: int) -> float:
    return 1.0 - ((correct_attempts + ALPHA) / (total_attempts + 2 * ALPHA))


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


def get_problem_cell_ids(user, min_attempts: int = 1, min_error: float = 0.4) -> list[int]:
    performances = (
        UserImagePerformance.objects
        .filter(user=user, total_attempts__gte=min_attempts)
        .select_related("image__cell")
    )

    result = set()

    for perf in performances:
        error = smoothed_error_rate(perf.correct_attempts, perf.total_attempts)
        if error >= min_error:
            result.add(perf.image.cell_id)

    return list(result)


def get_cell_similarity_scores(problem_cell_ids: list[int]) -> dict[int, float]:
    if not problem_cell_ids:
        return {}

    rows = CellSimilarity.objects.filter(
        source_cell_id__in=problem_cell_ids
    ).select_related("target_cell")

    scores = defaultdict(float)

    for row in rows:
        scores[row.target_cell_id] += row.weight

    return dict(scores)


def generate_trainer_images(user, limit: int = 10):
    personal_scores = get_personal_error_scores(user)
    problem_cell_ids = get_problem_cell_ids(user)
    similar_cell_scores = get_cell_similarity_scores(problem_cell_ids)

    attempted_image_ids = set(
        UserImagePerformance.objects
        .filter(user=user)
        .values_list("image_id", flat=True)
    )

    all_images = list(CellImage.objects.select_related("cell").all())

    scored = []

    for image in all_images:
        personal = personal_scores.get(image.id, 0.0)
        similarity = similar_cell_scores.get(image.cell_id, 0.0)
        novelty = 1.0 if image.id not in attempted_image_ids else 0.0

        score = (
            0.60 * personal
            + 0.30 * similarity
            + 0.10 * novelty
        )

        if score <= 0:
            continue

        if personal >= similarity and personal > 0:
            source = TestSessionImage.Source.PERSONAL_ERROR
        elif similarity > 0:
            source = TestSessionImage.Source.SIMILAR
        else:
            source = TestSessionImage.Source.NOVEL

        scored.append((image, source, score))

    scored.sort(key=lambda x: x[2], reverse=True)

    selected = scored[: max(1, int(limit * 0.8))]
    selected_ids = {item[0].id for item in selected}

    novel_pool = [
        image for image in all_images
        if image.id not in selected_ids
    ]

    random.shuffle(novel_pool)

    while len(selected) < limit and novel_pool:
        image = novel_pool.pop()
        selected.append((image, TestSessionImage.Source.NOVEL, 0.1))

    return selected[:limit]