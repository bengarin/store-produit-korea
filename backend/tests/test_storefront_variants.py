"""Étape « variantes et prix sur la boutique » : format public, image de variante, commande par variante."""

from decimal import Decimal

import pytest

from apps.catalog.models import ProductImage, ProductOption, ProductOptionValue, Variant, VariantOptionValue
from apps.inventory.models import StockMovement
from apps.orders.models import Order

from .conftest import order_payload, post_order

STORE = "/api/v1/store"


def with_variants(product, stocks, *, compare=None):
    """
    Produit actif « Contenance » 50 ml / 100 ml / 200 ml : stocks donnés dans cet ordre (None = non renseigné).
    La variante par défaut existante devient « 50 ml ».
    """
    option = ProductOption.objects.create(product=product, name="Contenance", position=0)
    values = [
        ProductOptionValue.objects.create(option=option, value=v, position=i)
        for i, v in enumerate(["50 ml", "100 ml", "200 ml"])
    ]
    default = product.variants.get()
    variants = [default]
    for i in (1, 2):
        variants.append(
            Variant.objects.create(product=product, price=Decimal(100 + 50 * i), position=i, title=values[i].value)
        )
    for variant, value, stock in zip(variants, values, stocks, strict=True):
        variant.title = value.value
        variant.stock_quantity = stock
        variant.save()
        VariantOptionValue.objects.create(variant=variant, option_value=value)
    if compare is not None:
        Variant.objects.filter(pk=variants[1].pk).update(compare_at_price=Decimal(compare))
    return variants


@pytest.mark.django_db
def test_format_public_options_disponibilite_et_sku(client, sellable):
    p = sellable(stock=10)
    _, v100, _ = with_variants(p, [10, 0, None], compare="199")
    Variant.objects.filter(pk=v100.pk).update(sku="MPC-100")
    data = client.get(f"{STORE}/products/{p.slug}").json()
    assert data["options"] == [{"name": "Contenance", "values": ["50 ml", "100 ml", "200 ml"]}]
    by_title = {v["title"]: v for v in data["variants"]}
    assert by_title["50 ml"]["availability"] == "available" and by_title["50 ml"]["available"] is True
    assert by_title["100 ml"]["availability"] == "out_of_stock" and by_title["100 ml"]["available"] is False
    # Stock non renseigné : jamais présenté comme disponible.
    assert by_title["200 ml"]["availability"] == "unavailable" and by_title["200 ml"]["available"] is False
    assert by_title["100 ml"]["sku"] == "MPC-100" and by_title["100 ml"]["compareAtPrice"] == 199
    assert by_title["50 ml"]["image"] is None
    text = str(data)
    assert "stock_quantity" not in text and "stockQuantity" not in text and "40.00" not in text  # ni stock ni coût


@pytest.mark.django_db
def test_produit_sans_aucune_variante_disponible(client, sellable):
    p = sellable(stock=0)
    with_variants(p, [0, None, 0])
    assert client.get(f"{STORE}/products/{p.slug}").json()["inStock"] is False


@pytest.mark.django_db
def test_vente_sans_stock_reste_disponible(client, sellable):
    p = sellable(stock=0, allow_backorder=True)
    v = client.get(f"{STORE}/products/{p.slug}").json()["variants"][0]
    assert v["availability"] == "available"


@pytest.mark.django_db
def test_image_de_variante(staff, client, sellable, product, media):
    p = sellable(stock=5)
    v50, v100, _ = with_variants(p, [5, 5, 5])
    texture = ProductImage.objects.create(product=p, media=media(color=(1, 99, 1)), alt="Texture", position=1)
    api = staff()
    response = api.patch(f"/api/v1/admin/variants/{v100.pk}", {"imageId": texture.pk}, format="json")
    assert response.status_code == 200, response.content
    assert response.json()["imageId"] == texture.pk
    public = {v["title"]: v for v in client.get(f"{STORE}/products/{p.slug}").json()["variants"]}
    assert public["100 ml"]["image"]["alt"] == "Texture" and public["100 ml"]["image"]["src"].endswith(".webp")

    other = product(slug="autre")
    foreign = other.images.first()
    refused = api.patch(f"/api/v1/admin/variants/{v50.pk}", {"imageId": foreign.pk}, format="json")
    assert refused.status_code == 400 and "imageId" in refused.json()["error"]["fields"]

    # Duplication : l'image de la variante pointe vers l'image COPIÉE.
    copy = api.post(f"/api/v1/admin/products/{p.pk}/duplicate").json()
    copied = Variant.objects.get(product_id=copy["id"], title="100 ml")
    assert copied.image is not None and copied.image.product_id == copy["id"] and copied.image.alt == "Texture"

    # Suppression de l'image : la variante revient à la galerie (pas d'erreur).
    api.delete(f"/api/v1/admin/product-images/{texture.pk}")
    assert Variant.objects.get(pk=v100.pk).image_id is None


@pytest.mark.django_db
def test_commande_de_la_variante_choisie(client, sellable):
    p = sellable(stock=10)
    v50, v100, _ = with_variants(p, [10, 4, None])
    payload = order_payload([])
    payload["items"] = [{"productId": p.slug, "variantId": v100.pk, "qty": 2}, {"productId": p.slug, "qty": 1}]
    response = post_order(client, payload)
    assert response.status_code == 201, response.content
    data = response.json()
    assert data["totals"]["subtotal"] == 2 * 150 + 129  # prix de CHAQUE variante, recalculé par le serveur
    order = Order.objects.get()
    lines = {i.variant_id: i for i in order.items.all()}
    assert lines[v100.pk].unit_price == Decimal("150.00") and lines[v100.pk].variant_title == "100 ml"
    assert Variant.objects.get(pk=v100.pk).stock_quantity == 2  # décrément sur la bonne variante
    assert Variant.objects.get(pk=v50.pk).stock_quantity == 9
    assert StockMovement.objects.filter(variant=v100, delta=-2).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("index,reason", [(1, "out_of_stock"), (2, "stock_unknown")])
def test_variante_epuisee_ou_non_renseignee_jamais_commandee(client, sellable, index, reason):
    p = sellable(stock=10)
    variants = with_variants(p, [10, 0, None])
    payload = order_payload([])
    payload["items"] = [{"productId": p.slug, "variantId": variants[index].pk, "qty": 1}]
    response = post_order(client, payload)
    assert response.status_code == 409
    item = response.json()["error"]["items"][0]
    assert item["reason"] == reason and item["variantId"] == variants[index].pk
    assert item["name"] == f"Marque Crème test — {variants[index].title}"  # le client sait quelle variante
    assert not Order.objects.exists()


@pytest.mark.django_db
def test_variante_d_un_autre_produit_refusee(client, sellable):
    a = sellable(slug="a", stock=5)
    b = sellable(slug="b", stock=5)
    payload = order_payload([])
    payload["items"] = [{"productId": a.slug, "variantId": b.variants.get().pk, "qty": 1}]
    response = post_order(client, payload)
    assert response.status_code == 400 and not Order.objects.exists()


@pytest.mark.django_db
def test_code_promo_calcule_sur_le_prix_de_la_variante(client, sellable):
    from apps.promotions.models import Coupon

    p = sellable(stock=10)
    _, _, v200 = with_variants(p, [10, 10, 10])
    Coupon.objects.create(code="MINI190", type="fixed_amount", value=Decimal("20"), min_subtotal=Decimal("190"))
    base = {"code": "MINI190", "items": [{"productId": p.slug, "qty": 1}]}
    assert client.post(f"{STORE}/promo-codes/validate", base, format="json").json()["valid"] is False  # 129 DH
    base["items"][0]["variantId"] = v200.pk  # 200 DH
    assert client.post(f"{STORE}/promo-codes/validate", base, format="json").json()["valid"] is True
