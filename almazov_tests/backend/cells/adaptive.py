from django.db.models import F, FloatField, ExpressionWrapper, Value
from django.db.models.functions import Coalesce
from .models import UserImagePerformance, GlobalImageStats, CellImage
from django.db.models import Q
import random
from collections import defaultdict
import math

ALPHA = 1  # сглаживание


def personal_scores_queryset(user):
    return UserImagePerformance.objects.filter(
        user=user
    ).annotate(
        error_rate=ExpressionWrapper(
            1 - (
                (F("correct_attempts") + ALPHA) /
                (F("total_attempts") + 2 * ALPHA)
            ),
            output_field=FloatField()
        )
    )

def get_user_error_images(user):
    return UserImagePerformance.objects.filter(
        user=user,
        total_attempts__gt=0
    ).exclude(
        correct_attempts=F("total_attempts")
    ).values_list("image_id", flat=True)


def compute_user_similarity(user):
    user_errors = set(get_user_error_images(user))

    if not user_errors:
        return {}

    similarities = {}

    other_users = UserImagePerformance.objects.exclude(
        user=user
    ).values_list("user_id", flat=True).distinct()

    for other_id in other_users:
        other_errors = set(
            UserImagePerformance.objects.filter(
                user_id=other_id,
                total_attempts__gt=0
            ).exclude(
                correct_attempts=F("total_attempts")
            ).values_list("image_id", flat=True)
        )

        intersection = len(user_errors & other_errors)

        if intersection == 0:
            continue

        sim = intersection / math.sqrt(
            len(user_errors) * len(other_errors)
        )

        similarities[other_id] = sim

    return similarities


def collaborative_scores(user):
    similarities = compute_user_similarity(user)

    if not similarities:
        return {}

    scores = defaultdict(float)
    weights = defaultdict(float)

    for other_id, sim in similarities.items():
        performances = UserImagePerformance.objects.filter(
            user_id=other_id,
            total_attempts__gt=0
        )

        for p in performances:
            error = 1 - (p.correct_attempts / p.total_attempts)

            scores[p.image_id] += sim * error
            weights[p.image_id] += sim

    final_scores = {}

    for image_id in scores:
        if weights[image_id] > 0:
            final_scores[image_id] = scores[image_id] / weights[image_id]

    return final_scores


def global_scores():
    return {
        stat.image_id: 1 - (
            (stat.total_correct + ALPHA) /
            (stat.total_attempts + 2 * ALPHA)
        )
        for stat in GlobalImageStats.objects.all()
    }


def novelty_score(attempts):
    return math.exp(-attempts)


def generate_trainer_images(user, limit=20):

    personal_qs = personal_scores_queryset(user)
    personal_dict = {
        p.image_id: p.error_rate
        for p in personal_qs
    }

    collab_dict = collaborative_scores(user)
    global_dict = global_scores()

    images = CellImage.objects.all()

    scored = []

    for image in images:
        p = personal_dict.get(image.id, 0.5)
        c = collab_dict.get(image.id, 0.5)
        g = global_dict.get(image.id, 0.5)

        perf = personal_qs.filter(image=image).first()
        attempts = perf.total_attempts if perf else 0

        n = novelty_score(attempts)

        score = (
            0.5 * p +
            0.3 * c +
            0.15 * g +
            0.05 * n
        )

        scored.append((score, image))

    scored.sort(reverse=True, key=lambda x: x[0])

    return [img for _, img in scored[:limit]]

def generate_random_images(limit=20):
    images = list(CellImage.objects.all())
    random.shuffle(images)
    return images[:limit]