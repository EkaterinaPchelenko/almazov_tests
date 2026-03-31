import math
from collections import defaultdict

from cells.models import CellImage, ImageSimilarity, UserImagePerformance

PERSONAL_WEIGHT = 0.6
SIMILARITY_WEIGHT = 0.3
NOVELTY_WEIGHT = 0.1
MIN_PERSONAL_SCORE = 0.4


def get_personal_scores(user):
    result = {}
    qs = UserImagePerformance.objects.filter(user=user)

    for perf in qs:
        error_rate = 1 - ((perf.correct_attempts + 1) / (perf.total_attempts + 2))
        result[perf.image_id] = error_rate

    return result


def get_similarity_scores(problem_image_ids):
    scores = defaultdict(float)

    similarities = ImageSimilarity.objects.filter(
        image_from_id__in=problem_image_ids
    ).order_by("-similarity_score")

    for sim in similarities:
        scores[sim.image_to_id] += sim.similarity_score

    return scores


def generate_trainer_images(user, limit=10):
    personal_scores = get_personal_scores(user)

    problem_image_ids = [
        image_id
        for image_id, score in personal_scores.items()
        if score >= MIN_PERSONAL_SCORE
    ]

    similarity_scores = get_similarity_scores(problem_image_ids)

    final_scores = []

    all_images = CellImage.objects.all()

    perf_map = {
        perf.image_id: perf
        for perf in UserImagePerformance.objects.filter(user=user)
    }

    for image in all_images:
        personal = personal_scores.get(image.id, 0.0)
        similar = similarity_scores.get(image.id, 0.0)

        perf = perf_map.get(image.id)
        attempts = perf.total_attempts if perf else 0
        novelty = math.exp(-attempts)

        score = (
            PERSONAL_WEIGHT * personal +
            SIMILARITY_WEIGHT * similar +
            NOVELTY_WEIGHT * novelty
        )

        final_scores.append((score, image))

    final_scores.sort(key=lambda x: x[0], reverse=True)
    return [image for _, image in final_scores[:limit]]