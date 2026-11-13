"""
Ajoute les sous-catégories d'exemple du menu « Catégories » (libellés de la maquette), modifiables ensuite
dans Admin → Catégories.

    python manage.py seed_menu_categories --dry-run   # aperçu : AUCUNE écriture
    python manage.py seed_menu_categories             # ajoute ce qui manque

Règles :
- facultatif : le menu fonctionne sans (il affiche alors les catégories seules) ;
- idempotent : une sous-catégorie déjà présente (même identifiant) n'est ni modifiée ni dupliquée, même si
  elle a été renommée, déplacée ou masquée dans l'admin ;
- n'ajoute que des sous-catégories : aucun produit n'y est rattaché (à faire dans l'admin), aucune autre
  donnée n'est touchée ; aucune migration.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Category

# (catégorie parente, identifiant, libellé FR, libellé AR [À VÉRIFIER par une personne arabophone])
EXAMPLES = [
    ("hydratation", "gels-apaisants", "Gels apaisants", "جل مهدّئ"),
    ("hydratation", "cremes-hydratantes", "Crèmes hydratantes", "كريمات مرطّبة"),
    ("eclat", "cremes-anti-taches", "Crèmes anti-taches", "كريمات مضادة للبقع"),
    ("eclat", "soins-du-teint", "Soins du teint", "العناية بإشراقة البشرة"),
    ("anti-age", "contour-des-yeux", "Contour des yeux", "محيط العينين"),
    ("anti-age", "patchs-yeux", "Patchs yeux", "لصقات العينين"),
]


class Command(BaseCommand):
    help = "Ajoute les sous-catégories d'exemple du menu (idempotent). --dry-run : aperçu sans écriture."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Prévisualise sans rien écrire.")

    def handle(self, *args, dry_run=False, **options):
        lines = []
        with transaction.atomic():
            for parent_slug, slug, name, name_ar in EXAMPLES:
                parent = Category.objects.filter(slug=parent_slug).first()
                if parent is None:
                    lines.append(f"- {name} : ignorée (catégorie « {parent_slug} » absente)")
                    continue
                if Category.objects.filter(slug=slug).exists():
                    lines.append(f"- {name} : déjà présente, laissée telle quelle")
                    continue
                lines.append(f"- {name} ({name_ar}) → sous « {parent.name} » : {'à créer' if dry_run else 'créée'}")
                if not dry_run:
                    position = parent.children.count()
                    Category.objects.create(
                        slug=slug, name=name, name_ar=name_ar, parent=parent, position=position, is_active=True
                    )
        mode = "APERÇU (--dry-run) : rien n'a été écrit" if dry_run else "AJOUT"
        self.stdout.write(f"Sous-catégories du menu — {mode}\n" + "\n".join(lines) + "\n")
