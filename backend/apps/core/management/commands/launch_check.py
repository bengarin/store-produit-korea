"""
Vérification AVANT ouverture de la boutique — LECTURE SEULE (rien n'est modifié) :

    DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py launch_check

❌ bloquant · ⚠️ à vérifier · ✅ correct. Code de sortie 1 s'il reste un point bloquant.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Q

from apps.accounts.models import User
from apps.accounts.roles import Role
from apps.accounts.twofactor import enabled as two_factor_enabled
from apps.catalog.models import Product, Variant
from apps.notifications.services import configured as email_configured
from apps.orders.models import Order
from apps.promotions.models import Coupon
from apps.shipping.models import ShippingZone
from apps.store_settings.models import StoreSettings

TEST_MARKERS = Q(ship_full_name__istartswith="test") | Q(ship_full_name__istartswith="client test")


class Command(BaseCommand):
    help = "Vérifie que la boutique est prête à ouvrir (lecture seule)."

    def handle(self, *args, **options):
        self.blockers = 0
        self.warnings = 0
        self.section("Configuration")
        self.item(not settings.DEBUG, "DEBUG désactivé", "DEBUG est activé")
        self.item(len(settings.SECRET_KEY) >= 40, "Clé secrète définie", "DJANGO_SECRET_KEY absente ou trop courte")
        self.item(
            bool(settings.ALLOWED_HOSTS) and "*" not in settings.ALLOWED_HOSTS,
            "ALLOWED_HOSTS précis",
            "ALLOWED_HOSTS vide ou « * »",
        )
        self.item(
            settings.SITE_URL.startswith("https://"),
            f"SITE_URL en HTTPS ({settings.SITE_URL})",
            "SITE_URL absente ou pas en https://",
        )
        self.item(
            getattr(settings, "SESSION_COOKIE_SECURE", False),
            "Cookies Secure",
            "Cookies non Secure (réglages de production non utilisés ?)",
        )
        self.item(
            {"owner", "admin"} <= set(settings.TWO_FACTOR_REQUIRED_ROLES),
            "2FA obligatoire Propriétaire/Admin",
            "2FA non obligatoire pour Propriétaire/Admin",
        )
        self.item(
            settings.TRUSTED_PROXY_COUNT > 0,
            f"Proxy de confiance : {settings.TRUSTED_PROXY_COUNT}",
            "TRUSTED_PROXY_COUNT = 0 : correct seulement si Django reçoit les visiteurs SANS proxy",
            blocking=False,
        )
        self.item(
            email_configured(),
            "E-mail configuré",
            "E-mail non configuré : aucune alerte de commande ne part",
            blocking=False,
        )
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        self.item(not plan, "Migrations appliquées", f"{len(plan)} migration(s) non appliquée(s)")
        backend = settings.CACHES["default"]["BACKEND"]
        shared = not backend.endswith(("locmem.LocMemCache", "dummy.DummyCache"))
        if shared and backend.endswith("db.DatabaseCache"):
            shared = settings.CACHES["default"]["LOCATION"] in connection.introspection.table_names()
        self.item(
            shared,
            "Cache partagé entre processus (limites anti-abus fiables)",
            "Cache non partagé ou table absente : lancer « manage.py createcachetable »",
        )
        index = Path(settings.FRONTEND_DIST_DIR) / "index.html"
        self.item(index.exists(), f"Front construit ({index})", f"index.html introuvable ({index})")
        media = Path(settings.MEDIA_ROOT)
        self.item(
            media.is_dir() and _writable(media),
            f"Dossier médias accessible en écriture ({media})",
            f"Dossier médias absent ou en lecture seule ({media})",
        )

        self.section("Informations légales et boutique (à fournir par le propriétaire)")
        s = StoreSettings.load()
        for field, label in (
            ("legal_name", "Raison sociale"),
            ("legal_address", "Adresse"),
            ("ice", "ICE"),
            ("rc", "RC"),
            ("if_number", "IF"),
        ):
            self.item(bool(getattr(s, field)), f"{label} renseigné", f"{label} manquant (factures)")
        self.item(
            s.vat_rate is not None,
            f"TVA configurée ({s.vat_rate} %)",
            "Taux de TVA non renseigné : à confirmer avec le comptable",
            blocking=False,
        )
        self.item(bool(s.whatsapp_number), "Numéro WhatsApp renseigné", "Numéro WhatsApp vide", blocking=False)
        self.item(
            bool(s.contact_phone or s.contact_email),
            "Coordonnées de contact",
            "Aucune coordonnée de contact",
            blocking=False,
        )
        self.item(ShippingZone.objects.exists(), "Zones de livraison", "Aucune zone de livraison")

        self.section("Catalogue (données réelles)")
        active = Product.objects.filter(status=Product.Status.ACTIVE)
        self.item(active.exists(), f"{active.count()} produit(s) actif(s)", "Aucun produit actif")
        tracked = Variant.objects.filter(product__in=active, track_inventory=True, allow_backorder=False)
        unknown = list(tracked.filter(stock_quantity__isnull=True).values_list("product__slug", "title"))
        self.item(
            not unknown,
            "Stock réel saisi pour toutes les variantes",
            f"Stock NON renseigné : {_fmt(unknown)} (non commandables)",
        )
        zero = list(tracked.filter(stock_quantity__lte=0).values_list("product__slug", "title"))
        self.item(
            not zero,
            "Aucune variante à 0",
            f"Stock à 0 (à confirmer : vrai stock ou reste de test ?) : {_fmt(zero)}",
            blocking=False,
        )
        free = list(Variant.objects.filter(product__in=active, price__lte=0).values_list("product__slug", flat=True))
        self.item(not free, "Tous les prix > 0", f"Prix nul : {', '.join(free)}")
        tests = list(
            active.filter(Q(slug__istartswith="test") | Q(name__istartswith="test")).values_list("slug", flat=True)
        )
        self.item(not tests, "Aucun produit de test actif", f"Produits de test actifs : {', '.join(tests)}")
        no_image = list(active.filter(images__isnull=True).values_list("slug", flat=True))
        self.item(not no_image, "Tous les produits actifs ont une image", f"Sans image : {', '.join(no_image)}")
        self.warn_info("Vérifiez à la main les prix et les textes de chaque produit avant l'ouverture.")

        self.section("Données de test (la base de production doit en être exempte)")
        test_orders = Order.objects.filter(TEST_MARKERS).count()
        self.item(
            test_orders == 0,
            "Aucune commande de test",
            f"{test_orders} commande(s) de test (nom « Test… ») : base de développement ?",
        )
        self.item(
            Order.objects.count() == 0,
            "Aucune commande avant l'ouverture",
            f"{Order.objects.count()} commande(s) déjà présentes : s'assurer qu'elles sont réelles",
            blocking=False,
        )
        demo = list(Coupon.objects.filter(is_active=True, code__in=["NATURE10"]).values_list("code", flat=True))
        self.item(
            not demo, "Aucun code promo de démonstration actif", f"Code de démonstration actif : {', '.join(demo)}"
        )

        self.section("Comptes de l'équipe")
        for user in User.objects.filter(
            is_active=True, groups__name__in=[Role.OWNER.value, Role.ADMIN.value]
        ).distinct():
            self.item(
                two_factor_enabled(user),
                f"2FA activée : {user.email}",
                f"2FA non activée : {user.email} (obligatoire à la 1re connexion)",
                blocking=False,
            )
        demo_users = list(
            User.objects.filter(is_active=True, email__iendswith="@exemple.ma").values_list("email", flat=True)
        )
        self.item(not demo_users, "Aucun compte d'exemple actif", f"Comptes d'exemple actifs : {', '.join(demo_users)}")

        self.stdout.write("")
        summary = f"{self.blockers} point(s) bloquant(s), {self.warnings} à vérifier."
        if self.blockers:
            self.stdout.write(self.style.ERROR(f"NON PRÊT — {summary}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS(f"PRÊT techniquement — {summary}"))

    # --- Affichage -------------------------------------------------------------------------
    def section(self, title):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{title}"))

    def item(self, ok, good, bad, blocking=True):
        if ok:
            self.stdout.write(f"  ✅ {good}")
        elif blocking:
            self.blockers += 1
            self.stdout.write(self.style.ERROR(f"  ❌ {bad}"))
        else:
            self.warnings += 1
            self.stdout.write(self.style.WARNING(f"  ⚠️ {bad}"))

    def warn_info(self, text):
        self.warnings += 1
        self.stdout.write(self.style.WARNING(f"  ⚠️ {text}"))


def _writable(path: Path) -> bool:
    import os

    return os.access(path, os.W_OK)


def _fmt(pairs) -> str:
    return ", ".join(
        f"{slug}{f' ({title})' if title and title != 'Par défaut' else ''}" for slug, title in pairs[:10]
    ) + (" …" if len(pairs) > 10 else "")
