# NATURÉ — Korean & Natural Skincare (front-end React)

Boutique e-commerce **mobile-first** en React + Vite : accueil, liste produits, fiche produit, panier, commande, confirmation.

> ⚠️ **Démo front-end uniquement.** Il n'y a pas de backend : aucune commande n'est envoyée à un serveur, aucun paiement n'est traité. La commande est simulée dans le navigateur (le panier est gardé dans le `localStorage`).

## Lancer le projet

Prérequis : [Node.js](https://nodejs.org) 18 ou plus récent.

```bash
npm install      # installe les dépendances (une seule fois)
npm run dev      # lance le site sur http://localhost:5173
npm run build    # crée la version finale dans dist/
npm run preview  # teste la version finale en local
npm run lint     # vérifie la qualité du code (ESLint)
```

### Variables d'environnement

Copiez `.env.example` en `.env.local` si besoin. Sans `VITE_API_BASE_URL`, le site utilise les données locales (mode démo).
Aucun secret ne doit être mis dans ces variables : elles sont visibles dans le navigateur. Voir **`docs/BACKEND.md`**.

## Backend (API Django)

Le dossier `backend/` contient l'API (Django + MySQL). Démarrage local : voir **`backend/README.md`**.
Le site fonctionne toujours seul, avec ses données locales, tant que `VITE_API_BASE_URL` n'est pas défini.

## Où modifier quoi ?

| Je veux changer…                        | Fichier                                   | Quoi                                    |
|-----------------------------------------|-------------------------------------------|-----------------------------------------|
| **Frais de livraison**                  | `src/config/store.js`                     | `deliveryFee` (et `freeDeliveryThreshold`) |
| **Numéro WhatsApp**                     | `src/config/store.js`                     | `whatsappNumber` (ex. `'2126XXXXXXXX'`) |
| **Codes promo**                         | `src/config/store.js`                     | `promoCodes` (`NATURE10` = démo)        |
| **Villes du formulaire**                | `src/config/store.js`                     | `cities`                                |
| **Prix des produits**                   | `src/data/local/products.js`              | `price` de chaque produit               |
| **Textes produits** (ingrédients, etc.) | `src/data/local/products.js`              | `summary`, `ingredients`, `usage`…      |
| **Catégories**                          | `src/data/local/categories.js`            | `id` + `label`                          |
| **Mentions « prix provisoires »**       | `src/config/store.js`                     | `showDemoNotices`                       |
| **Photos des produits**                 | `src/assets/products/` + `productImages.js` | voir ci-dessous                         |
| **Visuel de l'accueil**                 | `src/assets/hero/`                        | mobile : `nature-hero-products.webp` (+ 640 px) · desktop : `nature-hero-products-wide.webp` (+ 1280 px) |
| **Ingrédients à l'honneur**            | `src/data/ingredients.js` + `src/assets/ingredients/` | textes, photos, cadrage (`focus`) et produits liés (`productIds`) |
| **Le rituel NATURÉ (3 étapes)**        | `src/data/ritual.js`                      | titre, texte, produit lié, photo et cadrage |
| **Feuilles (page confirmation)**        | `src/assets/backgrounds/`                 | remplacer les fichiers                  |
| **Couleurs / typo / arrondis**          | `src/styles/global.css`                   | variables en haut du fichier (`:root`)  |

### Photos produits

Les vraies photos sont rangées **un dossier par produit** dans `src/assets/products/<id>/` et déclarées dans **`src/data/local/productImages.js`** :

| Champ | Rôle |
|---|---|
| `cardImage` | packshot des cartes, du panier et du récapitulatif |
| `mainImage` | première image de la fiche produit |
| `galleryImages` | toutes les vues de la fiche (packshot, boîte, texture, ambiance…) |

Chaque image a un `fit` : `contain` (packshot sur fond blanc, posé sur fond crème, rien n'est rogné) ou `cover` (photo d'ambiance qui remplit le cadre).

Pour remplacer une photo : écrasez le fichier `.webp` en gardant son nom. Pour en ajouter une : déposez le fichier dans le dossier du produit, importez-le dans `productImages.js` et ajoutez-le à `galleryImages`.

## Ce qui est provisoire (à valider avant la mise en ligne)

- **Prix** : valeurs de démonstration (129 / 199 / 149 / 229 / 179 DH).
- **Frais de livraison** : 20 DH (démo).
- **Code promo** `NATURE10` (−10 %) : démo, à supprimer ou remplacer.
- **Photos** : vos photos réelles (archive `produit.rar`), recadrées et converties en WebP.
- **Textes produits** : rédigés à partir du nom du produit uniquement. Ingrédients complets, mode d'emploi et types de peau **à reprendre de l'emballage officiel**. Aucune allégation médicale.
- **Notes / avis clients** de la maquette : volontairement **non affichés** (pas de faux avis).

## Parcours disponibles

- Accueil → Produits → Fiche → Panier → Commande → Confirmation
- **Commander maintenant** (fiche produit) → Commande directe, **sans toucher au panier**. Si le panier contient déjà des articles, une case permet de les ajouter à cette commande.
- Favoris (♡) gardés sur l'appareil, accessibles depuis le menu.
- Validation du téléphone marocain : `06…`, `07…`, `05…` (10 chiffres) ou `+212…`.

## Structure (détails : `docs/BACKEND.md`)

```
src/
  api/           client.js (fetch, délai, erreurs), endpoints.js (routes REST)
  assets/        products/ (visuels), hero/, ingredients/, backgrounds/, brand/
  components/    Header, ProductCard, ProductGallery, CartItem, QuantitySelector,
                 OrderSummary, CheckoutForm, Accordion, MenuDrawer…
  config/        store.js ← réglages business · env.js ← variables d'environnement
  context/       CatalogContext (produits, catégories), CartContext (panier, promo, favoris), ToastContext
  data/          local/ (catalogue de démo : produits, photos, catégories), ingredients.js, ritual.js
  hooks/         useReveal, useMediaQuery
  pages/         HomePage, ProductsPage, ProductPage, CartPage, CheckoutPage, ConfirmationPage
  services/      accès aux données : produits, catégories, config, panier, favoris, commandes
  styles/        global.css (design system)
  utils/         currency, pricing (totaux d'affichage), phone, icons, storage
design/          fichiers sources (logo original) — non inclus dans le site
```

## Mise en ligne

Le site utilise des URL propres (`/produits`, `/panier`…). L'hébergeur doit renvoyer `index.html` pour toutes les routes :
- **Netlify** : déjà géré par `public/_redirects`.
- **Vercel / autre** : ajouter une règle de réécriture vers `/index.html`.
