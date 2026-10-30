import datetime as dt

from django.utils import timezone
from rest_framework.exceptions import ValidationError


def date_range(params, field="placed_at"):
    """?from=2026-10-01&to=2026-10-31 (dates du Maroc, bornes incluses) → filtres Django."""
    filters = {}
    tz = timezone.get_current_timezone()
    for key, lookup, shift in (("from", "gte", 0), ("to", "lt", 1)):
        raw = params.get(key)
        if not raw:
            continue
        try:
            day = dt.date.fromisoformat(raw)
        except ValueError as exc:
            raise ValidationError({key: ["Date attendue au format AAAA-MM-JJ."]}) from exc
        start = dt.datetime.combine(day + dt.timedelta(days=shift), dt.time.min)
        filters[f"{field}__{lookup}"] = timezone.make_aware(start, tz)
    return filters
