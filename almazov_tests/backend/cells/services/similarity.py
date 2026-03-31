from collections import defaultdict
import math

from django.db import transaction

from cells.models import ImageSimilarity, UserImagePerformance


def rebuild_image_similarity(min_common_users=2):
    user_errors = defaultdict(list)

    performances = UserImagePerformance.objects.filter(wrong_attempts__gt=0)

    for perf in performances:
        user_errors[perf.user_id].append(perf.image_id)

    pair_counts = defaultdict(int)
    image_user_counts = defaultdict(int)

    for _, image_ids in user_errors.items():
        unique_ids = list(set(image_ids))

        for image_id in unique_ids:
            image_user_counts[image_id] += 1

        for i in range(len(unique_ids)):
            for j in range(i + 1, len(unique_ids)):
                a, b = sorted((unique_ids[i], unique_ids[j]))
                pair_counts[(a, b)] += 1

    rows = []

    for (a, b), common_count in pair_counts.items():
        if common_count < min_common_users:
            continue

        similarity = common_count / math.sqrt(
            image_user_counts[a] * image_user_counts[b]
        )

        rows.append(
            ImageSimilarity(
                image_from_id=a,
                image_to_id=b,
                similarity_score=similarity,
                common_users_count=common_count,
            )
        )
        rows.append(
            ImageSimilarity(
                image_from_id=b,
                image_to_id=a,
                similarity_score=similarity,
                common_users_count=common_count,
            )
        )

    with transaction.atomic():
        ImageSimilarity.objects.all().delete()
        ImageSimilarity.objects.bulk_create(rows, batch_size=1000)