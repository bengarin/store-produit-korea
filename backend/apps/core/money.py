from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value) -> Decimal:
    """Arrondi commercial au centime (0,005 → 0,01), comme le front (Math.round(n * 100) / 100)."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def number(value: Decimal | None):
    """Decimal → nombre JSON (129 et non "129.00")."""
    if value is None:
        return None
    return int(value) if value == value.to_integral_value() else float(value)
