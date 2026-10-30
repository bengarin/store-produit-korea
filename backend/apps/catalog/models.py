"""
Catalogue : catégories, produits, options/variantes, images, pictos.
Voir docs/ARCHITECTURE.md §4. Montants en DECIMAL(10,2), jamais en float.
"""

from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q

from apps.media_library.models import MediaAsset

FOCAL_POSITION = RegexValidator(r"^\d{1,3}% \d{1,3}%$", "Format attendu : « 50%% 88%% » (horizontal puis vertical).")


class Timestamped(models.Model):
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True


class Category(Timestamped):
    slug = models.SlugField("identifiant URL", max_length=80, unique=True)
    name = models.CharField("nom", max_length=100)
    parent = models.ForeignKey(
        "self", verbose_name="parente", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    position = models.PositiveIntegerField("ordre", default=0)
    is_active = models.BooleanField("visible", default=True)
    description = models.TextField("description", blank=True)
    seo_title = models.CharField("titre SEO", max_length=70, blank=True)
    seo_description = models.CharField("description SEO", max_length=160, blank=True)

    class Meta:
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["is_active", "position"], name="category_active_pos_idx")]

    def __str__(self):
        return self.name


class Product(Timestamped):
    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        ACTIVE = "active", "Actif"
        ARCHIVED = "archived", "Archivé"

    slug = models.SlugField("identifiant URL", max_length=120, unique=True)
    position = models.PositiveIntegerField("ordre d'affichage", default=0)
    brand = models.CharField("marque", max_length=100)
    name = models.CharField("nom", max_length=200)
    display_name = models.CharField("nom affiché", max_length=255, blank=True)
    short_description = models.CharField("phrase courte (cartes)", max_length=160, blank=True)
    summary = models.TextField("description", blank=True)
    description_html = models.TextField("description longue (HTML assaini)", blank=True)
    ingredients = models.JSONField("ingrédients", default=list, blank=True)
    benefits = models.JSONField("bienfaits", default=list, blank=True)
    usage_steps = models.JSONField("conseils d'utilisation", default=list, blank=True)
    skin_types = models.CharField("types de peau", max_length=255, blank=True)
    status = models.CharField("statut", max_length=10, choices=Status.choices, default=Status.DRAFT)
    categories = models.ManyToManyField(Category, through="ProductCategory", related_name="products", blank=True)
    hover_image = models.ForeignKey(
        "ProductImage",
        verbose_name="image au survol",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    hover_image_position = models.CharField("cadrage au survol", max_length=20, blank=True, validators=[FOCAL_POSITION])
    scene_image = models.ForeignKey(
        "ProductImage",
        verbose_name="image « en situation »",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    seo_title = models.CharField("titre SEO", max_length=70, blank=True)
    seo_description = models.CharField("description SEO", max_length=160, blank=True)
    og_image = models.ForeignKey(
        MediaAsset,
        verbose_name="image de partage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    published_at = models.DateTimeField("première mise en ligne", null=True, blank=True)

    class Meta:
        verbose_name = "produit"
        verbose_name_plural = "produits"
        ordering = ["position", "id"]
        indexes = [
            models.Index(fields=["status", "position"], name="product_status_pos_idx"),
            models.Index(fields=["brand"], name="product_brand_idx"),
        ]

    def __str__(self):
        return self.public_name

    @property
    def public_name(self):
        return self.display_name or f"{self.brand} {self.name}".strip()


class ProductCategory(models.Model):
    """Lien produit ↔ catégorie, ordonné : la 1re catégorie est la catégorie principale."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="category_links")
    # PROTECT : on ne supprime pas une catégorie encore utilisée (il faut d'abord la retirer des produits).
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="product_links")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["product", "category"], name="uniq_product_category")]

    def __str__(self):
        return f"{self.product_id} → {self.category_id}"


class ProductHighlight(models.Model):
    """Pictos de la fiche (icône choisie dans une liste fermée + libellé)."""

    class Icon(models.TextChoices):
        DROPLETS = "droplets", "Gouttes"
        LEAF = "leaf", "Feuille"
        SPARKLES = "sparkles", "Éclat"
        SUN = "sun", "Soleil"
        CITRUS = "citrus", "Agrume"
        EYE = "eye", "Œil"
        CLOCK = "clock", "Horloge"
        LAYERS = "layers", "Couches"
        FLASK = "flask", "Flacon"
        HAND = "hand", "Main"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="highlights")
    icon = models.CharField(max_length=20, choices=Icon.choices)
    label = models.CharField(max_length=60)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.label


class ProductImage(models.Model):
    class Fit(models.TextChoices):
        CONTAIN = "contain", "Packshot entier (fond crème)"
        COVER = "cover", "Photo d'ambiance (remplit le cadre)"

    class Kind(models.TextChoices):
        PACKSHOT = "packshot", "Packshot"
        INGREDIENT = "ingredient", "Ingrédient"
        IN_HAND = "in-hand", "En main"
        LIFESTYLE = "lifestyle", "Ambiance"
        TEXTURE = "texture", "Texture"
        IN_USE = "in-use", "Application"
        PACKAGING = "packaging", "Emballage"
        SCENE = "scene", "En situation"
        OTHER = "other", "Autre"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    media = models.ForeignKey(MediaAsset, on_delete=models.PROTECT, related_name="product_images")
    alt = models.CharField("texte alternatif", max_length=255, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    fit = models.CharField(max_length=10, choices=Fit.choices, default=Fit.CONTAIN)
    focal_position = models.CharField("cadrage", max_length=20, blank=True, validators=[FOCAL_POSITION])
    position = models.PositiveIntegerField(default=0)
    in_gallery = models.BooleanField("dans la galerie", default=True)

    class Meta:
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["product", "in_gallery", "position"], name="pimage_gallery_idx")]

    def __str__(self):
        return self.alt or f"Image {self.pk}"


class ProductOption(models.Model):
    """Ex. « Contenance ». 3 options maximum par produit (contrôlé par le service)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="options")
    name = models.CharField(max_length=50)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["product", "name"], name="uniq_option_name")]

    def __str__(self):
        return self.name


class ProductOptionValue(models.Model):
    option = models.ForeignKey(ProductOption, on_delete=models.CASCADE, related_name="values")
    value = models.CharField(max_length=50)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["option", "value"], name="uniq_option_value")]

    def __str__(self):
        return self.value


class Variant(Timestamped):
    """Ce qui est réellement vendu. Tout produit a au moins une variante (la variante par défaut)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    title = models.CharField("titre", max_length=160, blank=True)
    sku = models.CharField("SKU", max_length=64, null=True, blank=True, unique=True)
    barcode = models.CharField("code-barres", max_length=64, null=True, blank=True, unique=True)
    price = models.DecimalField("prix (DH)", max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField("prix barré (DH)", max_digits=10, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField("coût (DH) — jamais public", max_digits=10, decimal_places=2, null=True, blank=True)
    # NULL = stock NON RENSEIGNÉ (jamais inventé). Se modifie uniquement par un mouvement de stock (app inventory).
    stock_quantity = models.IntegerField("stock", null=True, blank=True, default=None)
    track_inventory = models.BooleanField("suivre le stock", default=True)
    allow_backorder = models.BooleanField("vendre sans stock", default=False)
    low_stock_threshold = models.PositiveIntegerField("seuil d'alerte", default=5)
    weight_grams = models.PositiveIntegerField("poids (g)", null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField("variante par défaut", default=False)
    # Photo affichée quand le client choisit cette variante (facultatif, image du même produit).
    image = models.ForeignKey(
        "ProductImage", verbose_name="image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    option_values = models.ManyToManyField(ProductOptionValue, through="VariantOptionValue", related_name="variants")

    class Meta:
        verbose_name = "variante"
        ordering = ["position", "id"]
        indexes = [
            models.Index(fields=["product", "position"], name="variant_product_pos_idx"),
            models.Index(fields=["stock_quantity"], name="variant_stock_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="variant_price_gte_0"),
            models.CheckConstraint(condition=Q(cost__isnull=True) | Q(cost__gte=0), name="variant_cost_gte_0"),
            models.CheckConstraint(
                condition=Q(compare_at_price__isnull=True) | Q(compare_at_price__gt=F("price")),
                name="variant_compare_at_gt_price",
            ),
            models.CheckConstraint(
                condition=Q(stock_quantity__isnull=True) | Q(stock_quantity__gte=0) | Q(allow_backorder=True),
                name="variant_stock_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.product.public_name} — {self.title or 'Par défaut'}"

    @property
    def stock_known(self):
        return self.stock_quantity is not None

    def available_quantity(self):
        """Quantité commandable : None = illimitée (stock non suivi ou vente sans stock), 0 si inconnue."""
        if not self.track_inventory or self.allow_backorder:
            return None
        return max(self.stock_quantity or 0, 0)

    @property
    def is_available(self):
        """Commandable maintenant. Stock non renseigné = NON commandable (sauf vente sans stock)."""
        available = self.available_quantity()
        return available is None or available > 0


class VariantOptionValue(models.Model):
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    option_value = models.ForeignKey(ProductOptionValue, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["variant", "option_value"], name="uniq_variant_option_value")]

    def __str__(self):
        return f"{self.variant_id} : {self.option_value_id}"
