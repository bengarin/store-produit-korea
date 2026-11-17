# Collections « Soins naturels » et « Beauté chinoise »

Une seule boutique, un seul panier, une seule commande. Une collection **regroupe des produits existants** :
un produit peut être dans 0, 1 ou 2 collections, avec **une seule fiche, un seul prix et un seul stock**.

## Où ça apparaît

| Endroit | Contenu |
|---|---|
| Menu « Boutique » (ordinateur et mobile) | Tous les produits + une carte par collection |
| Accueil (juste après la bannière) | Une carte par collection : image, description, « Découvrir la collection » |
| `/collections/<slug>` et `/ar/collections/<slug>` | Titre, description, image, produits de la collection, filtres, tri, tiroir mobile |
| Fiche produit | « Pays de fabrication : … » seulement s'il est renseigné ; ingrédients ou mention « non renseignée » |

Une collection n'est affichée que si elle est **visible** ET contient **au moins un produit en ligne**.
Sinon : rien dans le menu ni sur l'accueil, et sa page renvoie 404 (pas de page vide indexée par Google).

## Règles anti-allégation (vérifiées par le serveur)

| Collection | Règle | Effet |
|---|---|---|
| Soins naturels | Liste d'ingrédients obligatoire | Un produit sans ingrédients est refusé |
| Beauté chinoise | Pays de fabrication = Chine | Un produit sans origine « Chine » est refusé |

- Le refus est aussi appliqué si l'origine ou les ingrédients d'un produit changent **après** son ajout.
- Durcir la règle d'une collection déjà remplie est refusé tant que des produits ne la respectent pas.
- [LIMITE] La règle « ingrédients » prouve qu'une composition est renseignée, **pas** qu'elle est naturelle :
  la décision reste humaine. N'ajoutez un produit à « Soins naturels » qu'après lecture de sa liste INCI.

## Admin

- **Admin → Collections** : textes FR / AR, image (sinon photo du 1er produit), ordre, masquer, règles,
  bouton « Produits » (liste de tous les produits avec la raison d'un refus). Textes / règles : Propriétaire, Admin.
  Ranger des produits : + Éditeur.
- **Fiche produit → carte « Origine et collections »** : pays de fabrication (« Non renseigné » par défaut)
  et cases à cocher des collections (grisées avec la raison si la règle n'est pas respectée).

## Mise en place sur votre PC

1. Sauvegarde de la base MySQL.
2. `git pull`
3. `cd backend` puis `python manage.py migrate` : migrations `catalog 0008` (champ « pays de fabrication »,
   table des collections) et `catalog 0009` (crée les 2 collections, **sans aucun produit**).
4. `npm run build`
5. Pour chaque produit : renseigner le pays de fabrication **lu sur l'emballage**, puis ranger les produits.

## Aperçu TEST (produits fictifs)

**Admin → Collections → « Aperçu TEST »** : voir la page d'une collection avant d'avoir de vrais produits.

- Bandeau « TEST — données fictives », 6 produits inventés (« TEST · … », images dessinées, prix fictifs).
- Mobile / ordinateur, français / arabe (droite à gauche), filtres et tri utilisables.
- **Rien n'est enregistré** : aucun appel d'écriture au serveur, aucun vrai produit touché, aucun pays de fabrication.
  Panier et favoris fictifs en mémoire (le vrai panier du navigateur n'est pas modifié). Liens et recherche bloqués.
- Réservé aux comptes connectés à l'administration (`/admin/preview/collections/<slug>`). Les clients ne le voient pas :
  la vraie page `/collections/<slug>` reste cachée tant qu'aucun vrai produit n'est rangé.
- Les données fictives sont dans `src/admin/demo/collectionDemo.js` (chargé seulement par cet aperçu).
