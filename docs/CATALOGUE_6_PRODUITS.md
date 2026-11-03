# Catalogue — les 6 produits (préparation du 2026-11-03)

Source de vérité : `backend/catalog_import/catalogue.json`. Toutes les informations viennent des **photos réelles des
emballages** (archive `produit.rar`) ou du nom du produit. Rien n'est inventé ; ce qui n'est pas lisible est signalé.

> **État (2026-11-03) : validé et importé dans la base LOCALE**, les 6 produits en **brouillon**, prix 0 DH, non
> activés, stocks inchangés. Rien n'est en ligne : à refaire sur le serveur de production le moment venu.

## 1. Les 6 produits

| # | Produit | Marque | Format (lu sur l'emballage) | Catégories | Prix | Photos | Visuels |
|---|---------|--------|-----------------------------|------------|------|--------|---------|
| 1 | Aloe Vera Soothing Gel | Baroness | Pot — contenance **non visible** | Hydratation | **À définir** | 3 + scène | 2 |
| 2 | Yuja Niacin Anti Blemish Cream | SOME BY MI | Pot de 60 g | Éclat | **À définir** | 4 + scène | 2 |
| 3 | Tripeptide Cucumber Age-Defy Under Eye Patches | BIOVÈNE | 60 patchs (30 paires) + spatule | Anti-âge | **À définir** | 5 + scène | 4 |
| 4 | Vitamin Collagen Vital Cream | Quret | 50 g + crème contour des yeux 10 ml offerte | Anti-âge, Éclat | **À définir** | 2 + scène | 4 |
| 5 | **Vitamin Collagen Vital Eye Cream** (nouveau) | Quret | 25 ml + 10 ml offerts | Anti-âge, Éclat | **À définir** | 3 | 3 |
| 6 | Power Collagen Emulsion | ORJENA | Flacon de 100 ml | Hydratation, Anti-âge | **À définir** | 3 + scène | 4 |

Le produit n° 5 n'était pas au catalogue : ses 3 photos réelles étaient rangées par erreur dans la fiche n° 4
(`tube.webp`, `tube-box.webp` portent « COLLAGEN VITAL EYE CREAM »). L'import les rattache à la bonne fiche et les
**masque** de la galerie n° 4 (rien n'est supprimé).

## 2. Informations vérifiées (mentions lues sur les emballages)

| Produit | Mentions reprises dans la fiche |
|---------|--------------------------------|
| Baroness | Aloe vera pureté 99,85 % ; « 4 Free » : sans paraben, colorant artificiel, huile minérale, benzophénone ; aloe certifié USDA et IASC |
| SOME BY MI | Yuja extract 70 % ; Niacinamide 5 % ; 60 g ; « Anti Blemish » |
| Biovène | Tripeptide · Cucumber ; 60 patches / 30 pairs + spatula ; Barcelona |
| Quret Vital Cream | 50 g + 10 ml ; « brightening & elasticity » ; #VitaminEnergy #CollagenCare |
| Quret Eye Cream | 25 ml + 10 ml (« special gift ») ; « easy applicator for eye around » ; « brightening & elasticity » ; Made in Korea |
| ORJENA | Hydrolyzed collagen, Gelidium cartilagineum, Adenosine ; Skin elasticity · Skin nutrition · Refresh ; For all skin types ; 100 ml |

Chaque fiche contient : nom, marque, phrase courte, description, description longue (« Mentions de l'emballage »),
ingrédients mis en avant, bienfaits, mode d'utilisation (3–4 étapes génériques, cohérentes avec les visuels),
type de peau (ORJENA uniquement : seul emballage qui l'indique), 4 pictos, galerie, visuels marketing.

## 3. Informations manquantes

| Produit | [DONNÉES MANQUANTES] | [À VÉRIFIER] |
|---------|----------------------|--------------|
| Tous | Liste INCI complète · code-barres/SKU · prix · stock réel · traduction arabe relue | — |
| Baroness | Contenance (ml) · types de peau · mode d'emploi officiel | — |
| SOME BY MI | Types de peau | « Testé non comédogène » (sur un visuel, illisible sur les photos) |
| Biovène | Types de peau · temps de pose officiel | « 10-20 minutes » et « hydrogel » (visuels) |
| Quret Vital Cream | Types de peau · liste des vitamines | Le 10 ml offert = la crème n° 5 ? |
| Quret Eye Cream | Types de peau · photo seule du tube 25 ml · photo HD (500 px max) | Côté de boîte flou (niacinamide ? « 97 % ») |
| ORJENA | — | « Anti-wrinkle » (anti-rides) non repris : allégation à décider |

## 4. Prix, stock, arabe

- **Prix** : les prix actuels (129, 199, 149, 229, 179 DH) sont marqués `[DÉMO]` dans le code d'origine → **non repris**.
  L'import met chaque produit en **brouillon** avec un prix de 0 DH : c'est l'état « en attente de tarification »
  prévu par le système (le serveur refuse la mise en ligne tant que le prix vaut 0).
  ⚠️ Conséquence : après l'import, **la boutique n'affiche plus aucun produit** tant que les prix ne sont pas saisis
  et les produits remis « Actif » (Administration → Produits).
- **Stock** : jamais modifié. Le nouveau produit démarre « non renseigné » (non commandable).
- **Arabe** : aucun champ arabe écrit ni effacé. Les propositions de `GUIDE_TRADUCTION_PRODUITS.md` restent à relire.

## 5. Images

- Originaux conservés (jamais modifiés) : `backend/catalog_import/originaux/<produit>/{photos,visuels}/`
  — 135 Mo, **non versionné** (`.gitignore`), à garder aussi hors du serveur.
  `originaux/_non_importes/` : 6 « Avant / Après » générés (non authentiques) + 1 doublon en anglais.
- Images optimisées : `backend/catalog_import/images/<produit>/` (noms propres, un dossier par produit,
  `INDEX.json` = poids et empreintes). Réglage identique à l'administration : WebP qualité 85, 1 600 px max +
  version 640 px pour mobile, ratio conservé, jamais agrandi, sans métadonnées.
- Doublon détecté et écarté : `f507bc2b….png` = `Quret_Vitamin_Collagen_Vital_Cream.webp` (99,3 % identiques).

| Produit | Visuels marketing : avant → après | Photos galerie |
|---------|-----------------------------------|----------------|
| Baroness | 12,5 Mo → 388 Ko | déjà en WebP (5 à 80 Ko par photo) |
| SOME BY MI | 9,6 Mo → 291 Ko | déjà en WebP |
| Biovène | 20,2 Mo → 583 Ko | déjà en WebP |
| Quret Vital Cream | 21,4 Mo → 535 Ko | déjà en WebP |
| Quret Eye Cream | 16,0 Mo → 443 Ko | 436 Ko (PNG) → 25 Ko (photo principale) |
| ORJENA | 18,7 Mo → 406 Ko | déjà en WebP |
| **Total des fichiers utilisés** | **99,6 Mo → 3,9 Mo** (versions ordinateur + mobile, scènes comprises) | |

Une visite mobile d'une fiche charge les versions 640 px (≈ 20–48 Ko par visuel).

## 6. Script d'import — mode d'emploi

Comme une liste de courses : `catalogue.json` dit ce qu'il faut, le script compare avec la base et ne fait que la
différence.

```bash
cd backend
# 1. (seulement si les originaux changent) refaire les images optimisées — résultat identique à chaque fois
python manage.py prepare_catalog_images
# 2. Aperçu : AUCUNE écriture, liste exacte de ce qui changerait
python manage.py import_catalog --dry-run --report aperçu_import.md
# 3. Import réel (après votre accord) + rapport
python manage.py import_catalog --report rapport_import.md
```

- **Idempotent** : produit retrouvé par son identifiant (slug), image par son empreinte, lien image↔produit par
  (produit, image). Relancer ne crée aucun doublon (testé).
- Les 16 visuels déjà en base sont **reconnus** (même empreinte) : pas de doublon dans la médiathèque.
- **Aucune suppression** : une photo absente du fichier est masquée de la galerie (ligne et fichier conservés) ;
  catégories et pictos en trop sont signalés, jamais retirés.
- Visuels non listés dans le fichier : laissés tels quels et signalés. Aucun « Avant / Après » importé.
- Tout ou rien : en cas d'erreur, la base revient à son état initial.
- Tests : `backend/tests/test_import_catalog.py` (aperçu sans écriture, idempotence, stock/arabe protégés, fichier
  conservé).

Import local du 2026-11-03 : 5 produits mis à jour, 1 créé ; uniquement des ajouts en base (+1 produit, +1 variante,
+3 liens photo, +3 visuels, +4 médias, +2 catégories, +4 pictos) ; 0 suppression ; 0 stock modifié ; une 2e exécution
ne change plus rien.
