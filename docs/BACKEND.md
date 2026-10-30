# Préparation du Backend — Ma Petite Corée

> État actuel : le backend Django existe (`backend/`). Toutes les routes de ce contrat sont livrées sous
> `/api/v1/store` : catalogue (phase 1) et `/config`, `/promo-codes/validate`, `/orders` (phase 2).
> Contrat vérifié par `node scripts/check-api-contract.mjs` et les tests `backend/tests/`.
> Avant une mise en ligne en mode API : renseigner le stock réel et régler la limitation de débit derrière le proxy
> (voir `backend/README.md`, « Limites connues »).

## 1. Comment le front choisit sa source de données

| Variable (`.env`)       | Valeur          | Effet                                                              |
|-------------------------|-----------------|--------------------------------------------------------------------|
| `VITE_API_BASE_URL`     | vide (défaut)   | Mode **local** : catalogue de `src/data/local/`, commandes simulées |
| `VITE_API_BASE_URL`     | `/api/v1/store` | Mode **API** : catalogue (et plus tard commandes) via le backend   |
| `VITE_API_TIMEOUT_MS`   | `10000`         | Délai max d'une requête                                            |

⚠️ Toute variable `VITE_*` est **publique** (copiée dans le JavaScript envoyé au navigateur).
Ne jamais y mettre de clé API, mot de passe ou secret. Les secrets restent **côté serveur**.

## 2. Organisation du code

```
src/
  config/env.js          lecture des variables d'environnement (API_BASE_URL, DATA_SOURCE)
  config/store.js        réglages boutique (livraison, villes, WhatsApp, mentions démo)
  api/client.js          fetch + timeout + erreurs (ApiError) — seul fichier qui parle au réseau
  api/endpoints.js       liste des routes REST
  services/              une porte d'entrée par domaine (local OU API) :
    productService.js      produits (+ normalisation au format unique de l'interface)
    categoryService.js     catégories
    configService.js       configuration boutique (prête, pas encore branchée à l'interface)
    cartService.js         panier invité (navigateur)
    favoritesService.js    favoris (navigateur)
    orderService.js        envoi de commande, achat direct, dernière commande, lien WhatsApp
    storageKeys.js         clés localStorage / sessionStorage
  data/local/            données de démonstration (remplacées par l'API)
  context/CatalogContext  charge le catalogue une seule fois (écran d'attente/erreur en mode API)
  context/CartContext     état du panier, promo, favoris
  utils/pricing.js       calcul des totaux (AFFICHAGE uniquement)
  utils/phone.js         normalisation des numéros marocains
  utils/icons.js         nom d'icône → icône (les données ne contiennent que des noms)
```

Séparation : **données** (`data/`, API) → **services** (accès) → **contextes** (état) → **composants** (présentation).
Les composants n'importent jamais les données brutes directement.

## 3. Modèles de données attendus

### Product — `GET /products` → `{ items: Product[] }` (ou `Product[]`)

| Champ          | Type                         | Obligatoire | Utilisé pour                                  |
|----------------|------------------------------|-------------|-----------------------------------------------|
| `id`           | string (stable)              | oui         | URL `/produits/:id`, panier, favoris          |
| `slug`         | string                       | non (= id)  | URL lisible (prévu)                           |
| `brand`        | string                       | oui         | affichage                                     |
| `name`         | string                       | oui         | affichage                                     |
| `displayName`  | string                       | non         | nom complet (sinon `brand + name`)            |
| `cardLine`     | string                       | non         | phrase courte des cartes                      |
| `price`        | number (DH, TTC)             | oui         | affichage                                     |
| `categories`   | string[] (ids de catégories) | oui         | filtres, badges                               |
| `summary`      | string                       | oui         | description                                   |
| `highlights`   | `{ icon, label }[]`          | non         | pictos (icon ∈ droplets, leaf, sparkles, sun, citrus, eye, clock, layers, flask, hand) |
| `ingredients`  | string[]                     | non         | rubrique Ingrédients                          |
| `usage`        | string[]                     | non         | rubrique Conseils d'utilisation (étapes)      |
| `benefits`     | string[]                     | non         | rubrique Bienfaits                            |
| `skinTypes`    | string                       | non         | « Type de peau »                              |
| `stock`        | null                         | non         | toujours `null` : la quantité exacte n'est pas publiée |
| `inStock`      | boolean                      | non         | au moins une variante disponible (ajouté en phase 1) |
| `compareAtPrice` | number \| null             | non         | prix barré de la variante par défaut (phase 1) |
| `options`      | `{name, values[]}[]`         | non         | options dans l'ordre (sélecteur de la fiche) |
| `variants`     | `{id, title, sku, price, compareAtPrice, available, availability, isDefault, options, image}[]` | non | variantes (jamais le coût ni la quantité). `availability` : `available` \| `out_of_stock` (stock 0) \| `unavailable` (stock non renseigné) ; `image` : photo propre à la variante ou `null` |
| `seo`          | `{title, description, image}` | non        | métadonnées SEO (phase 1)                     |
| `descriptionHtml` | string (HTML assaini)     | non         | description longue (phase 1) — affichée sous le résumé dans « Description » depuis la phase 4, filtrée de nouveau par le navigateur (`utils/richText.js`) |
| `cardImage`    | Image                        | oui         | cartes, panier, récapitulatif                 |
| `mainImage`    | Image                        | oui         | 1re image de la fiche                         |
| `galleryImages`| Image[]                      | oui         | galerie de la fiche                           |
| `sceneImage`   | Image                        | non         | section « Le rituel » de l'accueil             |
| `hoverImage`   | Image                        | non         | 2e photo au survol (carrousel)                |

**Image** : `{ src: string (URL), src640?: string, alt: string, kind: string, fit: 'contain' | 'cover', position?: string }`

`id` = `slug` (le panier, les favoris et les liens du front utilisent cet identifiant : il doit rester stable).
(`fit: contain` = packshot fond blanc ; `cover` = photo d'ambiance).

### Category — `GET /categories` → `{ items: Category[] }`
`{ id: 'hydratation', label: 'Hydratation' }` — l'option « Tous » est ajoutée par l'interface.

### StoreConfig — `GET /config` (public, livré phase 2)
`{ brandName, whatsappNumber, deliveryFee, freeDeliveryThreshold, cities, allowOtherCity, maxQtyPerLine }`
— **sans** les codes promo. En mode API, le front l'utilise pour les villes, la livraison et WhatsApp.

### Commande — `POST /orders` (livré phase 2)
En-tête obligatoire : `Idempotency-Key: <UUID>` (généré par le navigateur, réutilisé pour un nouvel essai de la
même commande après une coupure réseau ⇒ jamais de double commande).
```json
{
  "customer": { "fullName": "…", "phone": "06 12 34 56 78", "city": "Casablanca", "address": "…" },
  "items": [{ "productId": "baroness-aloe-vera-gel", "variantId": null, "qty": 2 }],
  "promoCode": "CODE",
  "paymentMethod": "cod",
  "deliveryMethod": "home",
  "website": ""
}
```
Réponses :
- `201` (ou `200` si la même clé est renvoyée) : `{ number, createdAt, status, promoCode, totals: { itemCount, subtotal, discount, delivery, total }, items: [...] }` — aucune donnée personnelle ;
- `409 insufficient_stock` : `error.items = [{ productId, variantId, name, requested, available, reason: "stock_unknown" | "out_of_stock" | "insufficient" }]` ;
- `400 validation_error` : `error.fields` (ex. `customer.phone`, `promoCode`, `items`) ;
- `409 too_many_orders`, `409 idempotency_mismatch`, `429 throttled`.

`variantId` = variante choisie sur la fiche (absent = variante par défaut). Panier navigateur :
`[{ id, variantId?, qty }]` — même produit + même variante = une seule ligne ; l'ancien format `{ id, qty }` reste accepté.

Le front n'envoie **aucun prix** : seulement des identifiants et des quantités. Les totaux affichés dans le
navigateur sont indicatifs ; la confirmation affiche les totaux renvoyés par le serveur.

### Code promo — `POST /promo-codes/validate` (livré phase 2)
`{ code, items: [{ productId, qty }] }` → `{ valid: true, code, type: "percentage" | "fixed_amount" | "free_shipping", value, minSubtotal, discount }`
ou `{ valid: false, message }`. Le code est revérifié à la commande (dates, limites d'utilisation).

## 4. Règles de sécurité pour le backend

1. **Recalculer tous les montants côté serveur** (prix, remise, livraison, total) à partir de la base.
   Les totaux du navigateur (`utils/pricing.js`) servent seulement à l'affichage.
2. **Revalider le formulaire côté serveur** (nom, téléphone marocain, ville, adresse, quantités 1–20,
   produit existant et en stock). La validation du navigateur se contourne facilement.
3. **Codes promo** : jamais renvoyés au navigateur ; validation côté serveur uniquement.
4. **Anti-abus** : limitation de débit (rate limiting) et protection anti-spam sur `POST /orders`.
5. **CORS** : n'autoriser que le domaine de la boutique.
6. **Données personnelles** (nom, téléphone, adresse) : HTTPS obligatoire, accès restreint,
   durée de conservation définie (loi marocaine 09-08 / CNDP — [À VÉRIFIER avec un juriste]).
7. **Aucune authentification** n'est prévue côté front pour l'instant (pas de compte fictif).
   Favoris et panier restent dans le navigateur.

## 5. Brancher le backend — étapes

1. Développer les routes ci-dessus (Shopify, Supabase, Node/Express… : choix à faire).
2. Créer `.env.local` avec `VITE_API_BASE_URL=https://votre-api/api`.
3. `npm run build` → le catalogue et les commandes passent par l'API.
4. Mettre `showDemoNotices: false` dans `src/config/store.js` une fois prix et textes validés.
5. Option : brancher `configService.fetchStoreConfig()` pour piloter livraison/villes depuis le backend.
