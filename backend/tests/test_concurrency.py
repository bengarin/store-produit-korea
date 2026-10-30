"""
Concurrence RÉELLE sur MySQL : plusieurs requêtes simultanées (fils d'exécution, connexions séparées).
transaction=True : chaque fil voit les données validées des autres, comme en production.
"""

import threading
import uuid

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.catalog.models import Variant
from apps.inventory.models import StockMovement
from apps.orders.models import Order
from tests.conftest import order_payload


def run_parallel(n, payload_for, key_for=lambda i: str(uuid.uuid4())):
    barrier = threading.Barrier(n)
    results = [None] * n

    def worker(i):
        try:
            client = APIClient()
            barrier.wait()  # tous partent en même temps
            response = client.post(
                "/api/v1/store/orders", payload_for(i), format="json", HTTP_IDEMPOTENCY_KEY=key_for(i)
            )
            results[i] = (response.status_code, response.json())
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


@pytest.mark.django_db(transaction=True)
def test_dernier_article_un_seul_gagnant(sellable):
    sellable(stock=1)
    results = run_parallel(2, lambda i: order_payload([("creme-test", 1)], phone=f"06000000{i:02d}"))
    codes = sorted(code for code, _ in results)
    assert codes == [201, 409], results
    loser = next(body for code, body in results if code == 409)
    assert loser["error"]["code"] == "insufficient_stock" and loser["error"]["items"][0]["reason"] == "out_of_stock"
    assert Variant.objects.get().stock_quantity == 0
    assert Order.objects.count() == 1 and StockMovement.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_ruee_sur_le_stock_jamais_de_survente(sellable):
    sellable(stock=3)
    results = run_parallel(8, lambda i: order_payload([("creme-test", 1)], phone=f"06000001{i:02d}"))
    created = [body for code, body in results if code == 201]
    assert len(created) == 3, results
    assert len({body["number"] for body in created}) == 3  # numéros uniques
    assert Variant.objects.get().stock_quantity == 0


@pytest.mark.django_db(transaction=True)
def test_double_clic_simultane_une_seule_commande(sellable):
    sellable(stock=10)
    key = str(uuid.uuid4())
    payload = order_payload([("creme-test", 2)])
    results = run_parallel(3, lambda i: payload, key_for=lambda i: key)
    assert all(code in (200, 201) for code, _ in results), results
    assert len({body["number"] for _, body in results}) == 1
    assert Order.objects.count() == 1 and Variant.objects.get().stock_quantity == 8
