from django import template

register = template.Library()


@register.filter
def format_duration(value):
    if value is None:
        return "00:00"

    try:
        total_seconds = int(value)
    except (TypeError, ValueError):
        return "00:00"

    total_seconds = max(total_seconds, 0)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    return f"{minutes:02}:{seconds:02}"