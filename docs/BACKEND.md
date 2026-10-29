# Préparation du Backend — Ma Petite Corée

> État actuel : **aucun backend**. Le site fonctionne avec des données locales
> (`src/data/local/`) et les commandes sont **simulées**. Ce document décrit ce que
> le futur backend devra fournir pour que le front-end s'y branche sans refonte.

## 1. Comment le front choisit sa source de données

| Variable (`.env`)       | Valeur          | Effet                                                              |
|-------------------------|-----------------|--------------------------------------------------------------------|
| `VITE_API_BASE_URL`     | vide (défaut)   | Mode **local** : catalogue de `src/data/local/`, commandes simulées |
| `VITE_API_BASE_URL`     | `https://…/api` | Mode **API** : catalogue et commandes passent par le backend       |
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
| `stock`        | number \| null               | non         | prévu (pas encore affiché)                    |
| `cardImage`    | Image                        | oui         | cartes, panier, récapitulatif                 |
| `mainImage`    | Image                        | oui         | 1re image de la fiche                         |
| `galleryImages`| Image[]                      | oui         | galerie de la fiche                           |
| `sceneImage`   | Image                        | non         | section « Le rituel » de l'accueil             |
| `hoverImage`   | Image                        | non         | 2e photo au survol (carrousel)                |

**Image** : `{ src: string (URL), src640?: string, alt: string, fit: 'contain' | 'cover', position?: string }`
(`fit: contain` = packshot fond blanc ; `cover` = photo d'ambiance).

### Category — `GET /categories` → `{ items: Category[] }`
`{ id: 'hydratation', label: 'Hydratation' }` — l'option « Tous » est ajoutée par l'interface.

### StoreConfig — `GET /config` (public)
`{ deliveryFee, freeDeliveryThreshold, whatsappNumber, cities }` — **sans** les codes promo.

### Commande — `POST /orders`
Corps envoyé par le front (voir `buildOrderRequest`) :
```json
{
  "customer": { "fullName": "…", "phone": "+2126XXXXXXXX", "city": "Casablanca", "address": "…" },
  "items": [{ "productId": "baroness-aloe-vera-gel", "qty": 2 }],
  "promoCode": "CODE" ,
  "paymentMethod": "cod",
  "deliveryMethod": "home"
}
```
Réponse attendue : `{ "number": "…", "createdAt": "ISO-8601", "totals": { "itemCount", "subtotal", "discount", "delivery", "total" } }`

Le front n'envoie **aucun prix** : seulement des identifiants et des quantités.

### Code promo — `POST /promo-codes/validate` (prévu)
`{ code }` → `{ valid: boolean, percent?: number }`. Aujourd'hui la vérification est locale (démo `NATURE10`).

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
