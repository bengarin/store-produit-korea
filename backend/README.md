# Backend — Ma Petite Corée (Django + DRF + MySQL)

- **Phase 0** (fondations) : configuration, comptes de l'équipe et 5 rôles, connexion sécurisée,
  journal d'audit, format d'erreur commun, `/api/v1/health`, tests et lint.
- **Phase 1** (catalogue) : produits, catégories, options/variantes, images et médiathèque, SEO, statuts,
  API admin et API publique compatible avec le front, import des 5 produits de démonstration.
- **Phase 2** (commandes et clients) : stock réel par variante + historique des mouvements, commande en paiement à
  la livraison (transaction, verrouillage du stock, anti-doublon), clients, livraison, codes promo, statuts,
  facture imprimable, export Excel ; le formulaire de commande du site est branché sur l'API.

Pas encore de tableau de bord ni d'éditeur de thème (phases suivantes, voir `docs/ARCHITECTURE.md`).

## Prérequis

- Python 3.12 ou plus récent
- Docker (pour MySQL en local)
- Bibliothèques MySQL pour compiler `mysqlclient` :
  - Ubuntu/Debian : `sudo apt install pkg-config libmysqlclient-dev`
  - macOS : `brew install pkg-config mysql-client`

## Démarrer en local (étape par étape)

Toutes les commandes se lancent depuis la racine du dépôt, sauf indication.

```bash
# 1. Créer le fichier de configuration local (jamais commité)
cp backend/.env.example backend/.env
#    → remplir DJANGO_SECRET_KEY, DB_PASSWORD et MYSQL_ROOT_PASSWORD
#      (générer des valeurs : python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Démarrer MySQL 8.4 (conteneur, accessible seulement depuis votre machine)
docker compose --env-file backend/.env up -d

# 3. Installer Python et les dépendances
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements/dev.txt

# 4. Créer les tables
python manage.py migrate

# 5. Créer votre compte Propriétaire (le mot de passe est demandé, masqué)
python manage.py create_staff_user --email vous@exemple.ma --role owner

# 6. Importer les 5 produits de démonstration (images comprises) et la configuration actuelle du site
#    (villes, frais de livraison 20 DH, code de démo NATURE10, WhatsApp)
python manage.py import_demo_catalog
python manage.py import_store_config

# 7. Lancer l'API
python manage.py runserver
#    → http://127.0.0.1:8000/api/v1/health
#    → http://127.0.0.1:8000/api/v1/store/products
```

### Voir la boutique alimentée par MySQL

Dans un second terminal, à la racine du dépôt :

```bash
VITE_API_BASE_URL=/api/v1/store npm run dev     # http://localhost:5173
node scripts/check-api-contract.mjs             # doit afficher « DIFFERENCES 0 »
```

Vite relaie `/api` et `/media` vers Django (`vite.config.js`). Sans `VITE_API_BASE_URL`, le site reste en mode
démo local (commandes simulées), exactement comme avant.

⚠️ **Stock** : les produits importés ont un stock **non renseigné** et ne peuvent donc PAS être commandés
(message « momentanément indisponible »). Renseignez le stock réel de chaque variante :

```bash
# Exemple : 12 unités comptées pour la variante n° 3 (identifiants : GET /api/v1/admin/inventory)
curl … POST /api/v1/admin/inventory/adjust  {"variantId": 3, "mode": "set", "quantity": 12, "reason": "initial_count"}
```
(L'écran d'administration arrivera en phase 3 ; d'ici là, cet appel se fait avec une session admin.)

Arrêter MySQL : `docker compose --env-file backend/.env stop` (les données sont conservées dans le volume `mysql-data`).

> ⚠️ Si vous modifiez `DB_USER` après le premier démarrage, le script qui donne les droits sur la base de test
> (`docker/mysql/init/`) ne se relance pas : supprimez le volume (`docker compose --env-file backend/.env down -v`).

## Qualité

```bash
cd backend && source .venv/bin/activate
pytest                      # tests (sur une vraie base MySQL : test_<DB_NAME>)
pytest --cov=apps           # avec couverture
ruff check . && ruff format --check .   # lint + format
python manage.py makemigrations --check --dry-run   # aucune migration oubliée
```

## Configuration

| Fichier | Usage |
|---|---|
| `config/settings/base.py` | réglages communs (MySQL, sessions, CSRF, DRF, axes) |
| `config/settings/dev.py` | `manage.py` par défaut ; DEBUG, clé de dev si aucune |
| `config/settings/test.py` | `pytest` ; MySQL réel, hachage rapide |
| `config/settings/prod.py` | refuse de démarrer sans `DJANGO_SECRET_KEY` (≥ 40 car.) ni `DJANGO_ALLOWED_HOSTS` ; HTTPS, cookies sécurisés, HSTS |

Toutes les valeurs viennent de l'environnement / `backend/.env` (voir `.env.example`).

## Rôles

| Rôle (`--role`) | Libellé |
|---|---|
| `owner` | Propriétaire (un superutilisateur est aussi Propriétaire) |
| `admin` | Administrateur |
| `order_manager` | Gestionnaire de commandes |
| `content_editor` | Éditeur de contenu |
| `analyst` | Analyste (lecture seule) |

Un utilisateur a **un seul** rôle. Sans rôle : aucun accès à l'API admin.
Dans le code : `permission_classes = [HasRole.of(Role.OWNER, Role.ADMIN)]`.
Par défaut, **toute vue est fermée** (membre de l'équipe requis) ; une vue publique doit déclarer `AllowAny`.

## API disponible

| Méthode | Route | Accès | Réponse |
|---|---|---|---|
| GET | `/api/v1/health` | public | `{"status":"ok","database":"ok","version":"0.1.0"}` ou 503 |
| GET | `/api/v1/admin/auth/csrf` | public | dépose le cookie `mpc_csrftoken`, renvoie `{"csrfToken"}` |
| POST | `/api/v1/admin/auth/login` | public + en-tête `X-CSRFToken` | `{"user": {...}, "csrfToken"}` + cookie `mpc_session` (HttpOnly) |
| POST | `/api/v1/admin/auth/logout` | connecté + CSRF | 204 |
| GET | `/api/v1/admin/auth/me` | membre de l'équipe | `{"user": {id, email, firstName, lastName, role, roleLabel}}` |
| POST | `/api/v1/admin/auth/password` | membre + CSRF | `{currentPassword, newPassword}` → 204 |

### Boutique (publique, lecture seule, sans session) — `/api/v1/store/`

| Méthode | Route | Réponse |
|---|---|---|
| GET | `/products` | `{"items": [Product]}` — produits **actifs** seulement, au format du front (`id` = slug) |
| GET | `/products/{slug}` | `Product` ou 404 |
| GET | `/categories` | `{"items": [{"id": "hydratation", "label": "Hydratation"}]}` |

Jamais exposés : coût, quantité de stock exacte (`stock: null`, mais `inStock` et `variants[].available`),
brouillons, produits archivés, catégories masquées.

### Commande (publique) — `/api/v1/store/`

| Méthode | Route | Notes |
|---|---|---|
| GET | `/config` | `{brandName, whatsappNumber, deliveryFee, freeDeliveryThreshold, cities, allowOtherCity, maxQtyPerLine}` — jamais les codes promo |
| POST | `/promo-codes/validate` `{code, items:[{productId, qty}]}` | `{valid, code, type, value, minSubtotal, discount}` ou `{valid:false, message}` — 30/h par IP |
| POST | `/orders` + en-tête **`Idempotency-Key`** | 201 créée · 200 même commande renvoyée (double envoi) · 409 `insufficient_stock` (détail dans `error.items`) — 10/h par IP et 5/h par téléphone |

Corps de `/orders` : `{customer:{fullName, phone, city, address}, items:[{productId, variantId?, qty}], promoCode, paymentMethod:"cod", deliveryMethod:"home", website:""}`
(`website` = champ piège : rempli ⇒ refus). **Aucun montant envoyé par le navigateur n'est lu** : prix, remise et
livraison sont recalculés depuis MySQL. La réponse ne contient aucune donnée personnelle.

**Création d'une commande (une seule transaction)** : validation → verrouillage des variantes (`SELECT … FOR UPDATE`,
dans l'ordre des id) → contrôle du stock (stock non renseigné = non commandable, sauf « vente sans stock »)
→ recalcul des prix, du code promo (verrouillé) et de la livraison → numéro unique `MPC-AAAA-NNNNNN` → lignes avec
copie figée (nom, variante, SKU, prix, coût) → mouvements de stock → client (téléphone E.164) et adresse.

**Statuts** : `pending → confirmed → shipped → delivered` ; `pending|confirmed → cancelled` ;
`shipped|delivered → returned`. Annulation = remise en stock systématique et code promo libéré ; retour = remise en
stock par défaut (`"restock": false` si produits abîmés) ; livrée ⇒ payée ; retournée après livraison ⇒ remboursée.
Statistiques client recalculées depuis la base : commandes = non annulées, total dépensé = commandes livrées.

### Commandes, clients, stock, réglages (administration) — `/api/v1/admin/`

| Méthode | Route | Rôles (lecture / écriture) |
|---|---|---|
| GET | `/orders` (`?status=`, `?payment=`, `?from=AAAA-MM-JJ&to=`, `?city=`, `?search=` n°/téléphone/nom, `?customer=`) | O A M N |
| GET, PATCH | `/orders/{id}` (PATCH : `internalNote`) | O A M N / O A M |
| POST | `/orders/{id}/status` `{status, note, restock}` | O A M |
| GET | `/orders/{id}/invoice` (HTML imprimable) · `/orders/export.xlsx` (mêmes filtres) | O A M N |
| GET, PATCH | `/customers` (`?search=`, `?ordering=`) · `/customers/{id}` (+ commandes, adresses) | O A M N / O A M |
| GET | `/inventory` (`?state=unknown|low|out_of_stock`, `?search=`) | 5 rôles |
| POST | `/inventory/adjust` `{variantId, mode:"set"|"delta", quantity, reason, note}` | O A M |
| GET | `/inventory/movements` (`?variant=`, `?product=`, `?reason=`, `?order=`, `?from=&to=`) | 5 rôles |
| GET, POST, PATCH, DELETE | `/coupons`, `/coupons/{id}` | O A M N / O A |
| GET, POST, PATCH | `/shipping/zones`, `/shipping/cities` (+ `/{id}`) | O A M N / O A |
| GET, PATCH | `/settings` (WhatsApp, mentions légales de facture, limites) | O A M N / O A |

L'Éditeur de contenu n'a pas accès aux commandes ni aux clients (données personnelles).
Le coût d'achat des lignes de commande suit la même règle que le catalogue (O, A, Analyste).

### Catalogue (administration) — `/api/v1/admin/`

| Méthode | Route | Rôle |
|---|---|---|
| GET, POST | `/products` (`?status=`, `?category=`, `?search=`, `?ordering=`, `?page=`, `?page_size=`) | lecture : 5 rôles · création : O, A, E |
| GET, PATCH, DELETE | `/products/{id}` | suppression : O, A — refusée si actif (archiver d'abord) ou déjà commandé |
| POST | `/products/{id}/status` `{"status": "active"}` | O, A, E — activation vérifiée par le serveur |
| PUT | `/products/{id}/options` `[{"name": "Contenance", "values": ["50 ml"]}]` | O, A, E (3 options max) |
| GET, POST | `/products/{id}/variants` | O, A, E |
| GET, PATCH, DELETE | `/variants/{id}` | O, A, E — la dernière variante ne peut pas être supprimée |
| GET, POST | `/products/{id}/images` `{"mediaId", "alt", "fit", "kind", "focalPosition", "inGallery"}` | O, A, E |
| POST | `/products/{id}/images/reorder` `{"ids": [...]}` | O, A, E — la 1re image est l'image principale |
| PATCH, DELETE | `/product-images/{id}` | O, A, E |
| GET, POST | `/categories` | O, A, E |
| GET, PATCH, DELETE | `/categories/{id}` | suppression : O, A — refusée si elle contient des produits |
| POST | `/categories/reorder` | O, A, E |
| GET, POST (multipart `file`, `alt`) | `/media` | O, A, E |
| GET, PATCH, DELETE | `/media/{id}` | suppression : O, A — refusée si l'image est utilisée |

O = Propriétaire, A = Administrateur, E = Éditeur de contenu ; Gestionnaire de commandes et Analyste : lecture seule.
Le **coût** n'est visible que de O, A et Analyste, et modifiable que par O et A.

**Activation d'un produit** (`active`) — refusée tant qu'il manque : marque, nom, description, une catégorie,
une image dans la galerie, un prix > 0, et (si options) une valeur par option pour chaque variante, sans doublon.
Un produit actif ne peut pas être modifié de façon à redevenir incomplet (la modification est annulée).

**Images téléversées** : JPEG, PNG ou WebP vérifiés par leur contenu ; 10 Mo et 6000 px maximum, 200 px minimum ;
ré-encodées en WebP (1600 px max + version 640 px), métadonnées EXIF/GPS supprimées ; SVG, GIF, fichiers déguisés
et « bombes » de décompression refusés ; un fichier déjà présent n'est pas dupliqué.

Erreurs (toujours le même format) :
```json
{"error": {"code": "validation_error", "message": "Certaines informations sont invalides.", "fields": {"email": ["…"]}}}
```
Codes : `validation_error`, `parse_error`, `not_authenticated`, `authentication_failed`, `permission_denied`,
`csrf_failed`, `account_locked`, `not_found`, `method_not_allowed`, `throttled`, `service_unavailable`, `server_error`,
`conflict` et ses variantes (`product_active`, `product_in_use`, `category_in_use`, `media_in_use`, `last_variant`,
`variant_in_use`, `option_in_use`, `insufficient_stock`, `idempotency_mismatch`, `too_many_orders`,
`invalid_transition`, `coupon_in_use`).

## Sécurité en place

- Session Django (cookie `HttpOnly`, `SameSite=Lax`, 8 h, `Secure` en prod) + CSRF obligatoire, y compris sur la connexion.
- Mots de passe hachés en Argon2, 12 caractères minimum, mots de passe courants refusés.
- Verrouillage après 5 échecs (e-mail + IP, 1 h) — django-axes ; limitation de débit sur la connexion.
- Message d'échec identique que le compte existe ou non ; nouvelle session à chaque connexion.
- Journal d'audit en ajout seul : connexions, échecs, verrouillages, déconnexions, changements de mot de passe, création d'utilisateurs. Les mots de passe et jetons sont masqués automatiquement.
- Aucun secret dans le dépôt : `backend/.env` est ignoré par git.
- Commande publique : limitation par IP et par téléphone, champ piège, clé d'idempotence, validation du téléphone,
  de la ville, des produits actifs, des variantes et des quantités ; totaux toujours recalculés par le serveur.
- Export Excel : les textes saisis par les clients commençant par `=`, `+`, `-`, `@` sont neutralisés (pas d'injection
  de formule). Facture : toutes les données sont échappées (pas d'injection HTML).

## Limites connues (à traiter plus tard)

- **Stock réel des 5 produits non renseigné** : ils ne sont pas commandables tant qu'il n'est pas saisi.
- **Limitation de débit derrière un proxy/CDN** : l'adresse lue est `REMOTE_ADDR`. Derrière un proxy, TOUS les
  visiteurs partageraient la même limite (120 requêtes/min sur le catalogue, 10 commandes/heure) : à configurer
  (lecture fiable de `X-Forwarded-For`) AVANT la mise en ligne.
- Facture : mentions légales (ICE, RC, IF) à compléter dans les réglages — [À VÉRIFIER avec un comptable].
- Une adresse e-mail client n'est pas demandée (pas d'e-mail de confirmation pour l'instant).
- Médias stockés sur le disque local (`backend/media/`) ; stockage externe (S3/R2) à brancher à la mise en ligne.

- Limitation de débit stockée en mémoire locale : en production avec plusieurs processus, il faudra un cache partagé (ex. Redis).
- L'IP enregistrée est `REMOTE_ADDR` : derrière un proxy, il faudra configurer la lecture de `X-Forwarded-For`.
- 2FA (TOTP) recommandée pour le rôle Propriétaire : non incluse en phase 0.
