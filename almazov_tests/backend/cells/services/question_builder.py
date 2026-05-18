import random
from cells.models import Cell, CellImage, Level


def build_question(current_item, session, choice_count, allowed_cell_ids=None):
    level = session.level

    if level is None:
        return _image_to_name(current_item, choice_count, allowed_cell_ids)

    qtype = level.question_type

    if qtype == Level.QuestionType.IMAGE_TO_NAME:
        return _image_to_name(current_item, choice_count, allowed_cell_ids)

    elif qtype == Level.QuestionType.NAME_TO_IMAGE:
        return _name_to_image(current_item, choice_count, allowed_cell_ids)

    elif qtype == Level.QuestionType.MATCHING:
        return _matching(current_item, choice_count, allowed_cell_ids)

    return _image_to_name(current_item, choice_count, allowed_cell_ids)


def _image_to_name(current_item, choice_count, allowed_cell_ids):
    correct = current_item.image.cell.name

    qs = Cell.objects.exclude(id=current_item.image.cell_id)
    if allowed_cell_ids:
        qs = qs.filter(id__in=allowed_cell_ids)

    distractors = list(qs.values_list("name", flat=True))
    random.shuffle(distractors)

    options = [correct] + distractors[:choice_count - 1]
    random.shuffle(options)

    return {
        "type": "image_to_name",
        "image": current_item.image,
        "options": options,
        "correct": correct,
    }


def _name_to_image(current_item, choice_count, allowed_cell_ids):
    correct_cell = current_item.image.cell

    # правильная картинка
    correct_image = current_item.image

    qs = Cell.objects.exclude(id=correct_cell.id)
    if allowed_cell_ids:
        qs = qs.filter(id__in=allowed_cell_ids)

    distractor_cells = list(qs)
    random.shuffle(distractor_cells)

    distractor_images = []
    for cell in distractor_cells[:choice_count - 1]:
        img = cell.cell_images.order_by("?").first()
        if img:
            distractor_images.append(img)

    options = [correct_image] + distractor_images
    random.shuffle(options)

    return {
        "type": "name_to_image",
        "cell_name": correct_cell.name,
        "options": options,
        "correct_id": correct_image.id,
    }


def _matching(current_item, choice_count, allowed_cell_ids):
    qs = Cell.objects.all()
    if allowed_cell_ids:
        qs = qs.filter(id__in=allowed_cell_ids)

    cells = list(qs)
    random.shuffle(cells)

    selected = cells[:choice_count]

    pairs = []
    for cell in selected:
        img = cell.cell_images.order_by("?").first()
        if img:
            pairs.append({
                "cell_id": cell.id,
                "cell_name": cell.name,
                "image_id": img.id,
                "image_url": img.image.url,
            })

    # перемешиваем изображения
    shuffled_images = pairs.copy()
    random.shuffle(shuffled_images)

    return {
        "type": "matching",
        "pairs": pairs,
        "images": shuffled_images,
    }