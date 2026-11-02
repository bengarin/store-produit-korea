"""Phase 7 — vérification d'avant-ouverture : lecture seule, signale les points bloquants."""

import pytest
from django.core.management import call_command

from apps.catalog.models import Variant


@pytest.mark.django_db
def test_launch_check_signale_les_blocages_sans_rien_modifier(sellable, capsys):
    p = sellable(slug="creme-ok", stock=5)
    Variant.objects.filter(product=p).update(stock_quantity=None)
    before = list(Variant.objects.values_list("pk", "stock_quantity"))
    with pytest.raises(SystemExit) as exc:
        call_command("launch_check")
    out = capsys.readouterr().out
    assert exc.value.code == 1 and "NON PRÊT" in out
    assert "DJANGO_SECRET_KEY absente" in out and "ICE manquant" in out and "Stock NON renseigné : creme-ok" in out
    assert list(Variant.objects.values_list("pk", "stock_quantity")) == before  # rien n'est modifié
