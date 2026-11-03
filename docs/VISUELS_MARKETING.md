# Fiche produit « landing page » et visuels marketing

## Mise en page

- **Ordinateur (≥ 860 px)** : deux colonnes. À gauche, la galerie du produit (photos d'origine, miniatures, flèches,
  zoom au survol) reste **collée** pendant le défilement et s'arrête à la fin de la section produit (jamais sur les
  sections suivantes ni sur le pied de page). À droite : nom, prix, description, caractéristiques, quantité,
  « Ajouter au panier », « Commander maintenant », réassurance, **puis les visuels marketing**. Les onglets
  Description / Ingrédients / Conseils / Points forts restent sous les deux colonnes.
- **Mobile** : galerie en haut (non collante), informations et boutons, réassurance, puis visuels marketing qui
  apparaissent au défilement. Images à la largeur de l'écran (version 640 px, plus légère).
- **Arabe** : sens droite → gauche ; titres de sections traduits.
- Note et avis : **non affichés** (la boutique n'a pas d'avis clients ; rien n'est inventé).

## Sections (ordre fixe, une section sans visuel n'apparaît pas)

Présentation · Bienfaits · Ingrédients clés · Mode d'utilisation · Avant / Après · Comparaison · La marque · Autre.

## Administration — menu « Visuels marketing »

- Liste des produits avec le nombre de visuels affichés par langue (FR, AR, sans texte).
- Page d'un produit (aussi accessible depuis la fiche produit → « Gérer les visuels ») :
  - un **onglet par langue** : Français, Arabe (espace indépendant), Sans texte (affiché dans les deux langues) ;
  - **import multiple** (JPEG, PNG, WebP, 10 Mo max ; converti en WebP 1 600 px + version 640 px) avec catégorie ;
  - pour chaque visuel : catégorie, titre et description facultatifs, texte alternatif, afficher / masquer,
    monter / descendre, **remplacer l'image**, supprimer (Propriétaire et Admin ; l'image reste dans la bibliothèque).
- Droits : Propriétaire, Admin, Éditeur de contenu modifient ; Gestionnaire et Analyste consultent.
- Langue affichée sur la boutique en arabe : visuels **arabes** + sans texte ; si le produit n'a **aucun** visuel
  arabe, visuels français + sans texte (repli).

## Règles de contenu

- Les visuels marketing sont **séparés** des photos du produit (table distincte) : la galerie n'est jamais modifiée.
- **Avant / Après** : importé masqué ; ne s'affiche qu'après la case « photos authentiques (sans retouche, montage
  ni image générée) ». Sans elle, le serveur refuse l'affichage.
- Ne pas importer de visuel portant une promesse non vérifiée.

## Import réalisé en local (base de développement)

16 visuels (texte français) rattachés à leur produit :

| Produit | Visuels |
|---------|---------|
| Baroness Aloe Vera Soothing Gel | Présentation, Mode d'utilisation |
| SOME BY MI Yuja Niacin Cream | Présentation, Ingrédients clés |
| Biovène Eye Patches | Présentation, 2 × Bienfaits, Mode d'utilisation |
| Quret Vitamin Collagen Vital Cream | 2 × Présentation, Bienfaits, Mode d'utilisation |
| ORJENA Power Collagen Emulsion | Présentation, 2 × Bienfaits, Mode d'utilisation |

**Non importés :**
- 6 visuels « Avant / Après » : fichiers issus d'un générateur d'images (préfixe `hf_`), non authentiques ;
  certains suggèrent un résultat (imperfections disparues). Contraires à la règle « pas de faux avant/après ».
- 4 visuels d'un produit **absent du catalogue** : « Vitamin Collagen Vital **Eye** Cream » (tube 25 ml + 10 ml).
- Aucune capture d'écran de maquette (ordinateur / mobile) n'était présente dans les archives.

**[À VÉRIFIER] mentions présentes dans les visuels importés**, à confirmer sur les emballages avant publication :
« Aloe Vera 99,85 % » et « sans paraben, colorant artificiel, huile minérale, benzophénone » (Baroness) ;
« Niacinamide 5 % », « testé non comédogène », « format 60 g » (SOME BY MI) ; « 50 g + crème contour des yeux 10 ml
offerte » (Quret) ; « élasticité, nutrition », « collagène hydrolysé, gelidium, adénosine » (ORJENA) ;
« tripeptide » (Biovène). Aucun visuel arabe n'a été fourni.

## API

- Admin : `GET/POST /api/v1/admin/products/{id}/marketing-images`, `POST …/marketing-images/reorder`,
  `PATCH/DELETE /api/v1/admin/marketing-images/{id}` (PATCH `mediaId` = remplacer l'image).
- Public : champ `marketing` de la fiche produit (visuels affichables uniquement ; absent s'il n'y en a pas).
- Base : table `catalog_productmarketingimage` (migration `catalog 0005`, ajout seul).

## Visuels arabes (3 nov. 2026)

Ajoutés en langue « ar » via `backend/catalog_import/catalogue.json` (originaux : `originaux/<produit>/visuels_ar/`).
La version **française n'est pas modifiée** ; la version arabe affiche les visuels arabes du produit (règle existante :
si un produit a au moins un visuel arabe affiché, la fiche arabe ne montre que ceux-ci + « sans texte » ; sinon repli
sur le français — jamais de mélange de langues sur une fiche).

| Produit | Visuels arabes affichés | Masqués (à corriger) | Version arabe de la fiche |
|---|---|---|---|
| ORJENA | Bienfaits ×2, Mode d'utilisation | Présentation : « كبسولات » = « capsules » (le produit est une émulsion) | 3 visuels arabes |
| Baroness | Présentation (contient un faux bouton « اطلب الآن ») | Bienfaits : « (4 مجاني) » = « 4 gratuits » (traduction littérale de « 4 Free ») | 1 visuel arabe |
| Biovène | Présentation, Bienfaits, Mode d'utilisation | — | 3 visuels arabes |
| Quret Vital Cream | Présentation, Bienfaits, Mode d'utilisation | — | 3 visuels arabes |
| Quret Eye Cream | Présentation, Bienfaits, Mode d'utilisation | — | 3 visuels arabes |
| SOME BY MI | Présentation, Ingrédients clés, Mode d'utilisation | — (« testé non comédogène » : [À VÉRIFIER] comme en français) | 3 visuels arabes |

Non importés : 14 « avant / après » (images générées, non authentiques ; 5 portent des libellés français) →
`originaux/_non_importes/visuels_ar/`. Un visuel masqué s'active dans Administration → Visuels marketing après
correction du texte.

## Envoi en 4 parties (3 nov. 2026)

50 images reçues : 30 déjà en place, 14 déjà écartées (avant/après générés, doublon anglais), 6 nouvelles.
Ajoutées : SOME BY MI « Mode d'utilisation » (FR), Baroness « Bienfaits » (FR), Biovène « Présentation » et
« Mode d'utilisation » (AR). Écartées : 2 avant/après Biovène (FR et AR). Version française après ajout : Baroness 3
visuels, SOME BY MI 3, Biovène 4, Vital Cream 4, Eye Cream 3, ORJENA 4.

