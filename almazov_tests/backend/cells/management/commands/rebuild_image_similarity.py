import math
from collections import defaultdict
from itertools import combinations

from django.core.management.base import BaseCommand

from cells.models import ImageSimilarity, UserImagePerformance


class Command(BaseCommand):
    help = "Rebuild item-item similarity matrix for CellImage"

    def handle(self, *args, **options):
        image_to_users = defaultdict(set)

        qs = UserImagePerformance.objects.filter(
            total_attempts__gt=0,
            wrong_attempts__gt=0,
        ).values("user_id", "image_id")

        for row in qs:
            image_to_users[row["image_id"]].add(row["user_id"])

        image_ids = list(image_to_users.keys())
        pairs = []

        for image_a, image_b in combinations(image_ids, 2):
            users_a = image_to_users[image_a]
            users_b = image_to_users[image_b]

            common = len(users_a & users_b)
            if common == 0:
                continue

            similarity = common / math.sqrt(len(users_a) * len(users_b))
            if similarity < 0.05:
                continue

            pairs.append(
                ImageSimilarity(
                    image_from_id=image_a,
                    image_to_id=image_b,
                    similarity_score=similarity,
                    common_users_count=common,
                )
            )
            pairs.append(
                ImageSimilarity(
                    image_from_id=image_b,
                    image_to_id=image_a,
                    similarity_score=similarity,
                    common_users_count=common,
                )
            )

        ImageSimilarity.objects.all().delete()
        ImageSimilarity.objects.bulk_create(pairs, batch_size=1000)

        self.stdout.write(self.style.SUCCESS("Image similarity rebuilt"))