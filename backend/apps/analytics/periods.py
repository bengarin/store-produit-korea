"""
Périodes du tableau de bord et période de comparaison ÉQUIVALENTE.

Toutes les dates sont des jours calendaires à l'heure du Maroc (settings.TIME_ZONE = Africa/Casablanca) ;
les bornes sont converties en instants UTC par zoneinfo, ce qui gère les changements d'heure (ramadan).

Comparaisons :
- aujourd'hui            → hier
- 7 / 30 / 90 jours, personnalisée → les N jours qui précèdent immédiatement
- ce mois (du 1er à aujourd'hui)    → mois précédent, du 1er au même quantième (borné à la fin du mois)
- mois précédent (complet)          → le mois d'avant (complet)
- année en cours (1er janv. → aujourd'hui) → année précédente, même intervalle (29 févr. → 28 févr.)
"""

import calendar
import datetime as dt
from dataclasses import dataclass

from django.utils import timezone

PRESETS = ("today", "7d", "30d", "90d", "month", "last_month", "year", "custom")
MAX_DAYS = 366


@dataclass(frozen=True)
class Period:
    start: dt.date  # inclus
    end: dt.date  # inclus

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def bounds(self):
        """[début, fin) en instants conscients du fuseau : minuit local du 1er jour → minuit local du lendemain."""
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(dt.datetime.combine(self.start, dt.time.min), tz)
        end = timezone.make_aware(dt.datetime.combine(self.end + dt.timedelta(days=1), dt.time.min), tz)
        return start, end

    def as_dict(self):
        return {"from": self.start.isoformat(), "to": self.end.isoformat(), "days": self.days}


def _month_start(day: dt.date) -> dt.date:
    return day.replace(day=1)


def _month_end(day: dt.date) -> dt.date:
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def _same_day_previous_month(day: dt.date) -> dt.date:
    previous = _month_start(day) - dt.timedelta(days=1)
    return previous.replace(day=min(day.day, calendar.monthrange(previous.year, previous.month)[1]))


def _same_day_previous_year(day: dt.date) -> dt.date:
    year = day.year - 1
    return day.replace(year=year, day=min(day.day, calendar.monthrange(year, day.month)[1]))


def _preceding(period: Period) -> Period:
    end = period.start - dt.timedelta(days=1)
    return Period(end - dt.timedelta(days=period.days - 1), end)


def resolve(preset: str, today: dt.date, date_from: dt.date | None = None, date_to: dt.date | None = None):
    """Retourne (période, période de comparaison). `custom` exige date_from et date_to."""
    if preset == "today":
        current = Period(today, today)
        return current, _preceding(current)
    if preset in ("7d", "30d", "90d"):
        n = int(preset[:-1])
        current = Period(today - dt.timedelta(days=n - 1), today)
        return current, _preceding(current)
    if preset == "month":
        current = Period(_month_start(today), today)
        prev_start = _month_start(_month_start(today) - dt.timedelta(days=1))
        return current, Period(prev_start, _same_day_previous_month(today))
    if preset == "last_month":
        last = _month_start(today) - dt.timedelta(days=1)
        current = Period(_month_start(last), last)
        before = _month_start(last) - dt.timedelta(days=1)
        return current, Period(_month_start(before), _month_end(before))
    if preset == "year":
        current = Period(today.replace(month=1, day=1), today)
        return current, Period(today.replace(year=today.year - 1, month=1, day=1), _same_day_previous_year(today))
    if preset == "custom":
        current = Period(date_from, date_to)
        return current, _preceding(current)
    raise ValueError(preset)
