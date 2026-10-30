# Backend — Ma Petite Corée (Django + DRF + MySQL)

- **Phase 0** (fondations) : configuration, comptes de l'équipe et 5 rôles, connexion sécurisée,
  journal d'audit, format d'erreur commun, `/api/v1/health`, tests et lint.
- **Phase 1** (catalogue) : produits, catégories, options/variantes, images et médiathèque, SEO, statuts,
  API admin et API publique compatible avec le front, import des 5 produits de démonstration.

Pas encore de commandes, de tableau de bord ni d'éditeur de thème (phases suivantes, voir `docs/ARCHITECTURE.md`).

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

# 6. Importer les 5 produits de démonstration (images comprises)
python manage.py import_demo_catalog

# 7. Lancer l'API
python manage.py runserver
#    → http://127.0.0.1:8000/api/v1/health
#    → http://127.0.0.1:8000/api/v1/store/products
```

### Voir la boutique alimentée par MySQL (phase 1)

Dans un second terminal, à la racine du dépôt :

```bash
VITE_API_BASE_URL=/api/v1/store npm run dev     # http://localhost:5173
node scripts/check-api-contract.mjs             # doit afficher « DIFFERENCES 0 »
```

Vite relaie `/api` et `/media` vers Django (`vite.config.js`). Sans `VITE_API_BASE_URL`, le site reste en mode local.
⚠️ La **commande** ne fonctionne pas encore en mode API (`POST /orders` arrive en phase 2) : ne pas mettre en ligne
le mode API avant la phase 2.

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
`variant_in_use`, `option_in_use`).

## Sécurité en place

- Session Django (cookie `HttpOnly`, `SameSite=Lax`, 8 h, `Secure` en prod) + CSRF obligatoire, y compris sur la connexion.
- Mots de passe hachés en Argon2, 12 caractères minimum, mots de passe courants refusés.
- Verrouillage après 5 échecs (e-mail + IP, 1 h) — django-axes ; limitation de débit sur la connexion.
- Message d'échec identique que le compte existe ou non ; nouvelle session à chaque connexion.
- Journal d'audit en ajout seul : connexions, échecs, verrouillages, déconnexions, changements de mot de passe, création d'utilisateurs. Les mots de passe et jetons sont masqués automatiquement.
- Aucun secret dans le dépôt : `backend/.env` est ignoré par git.

## Limites connues (à traiter plus tard)

- Stock réel des 5 produits inconnu : importés avec « suivre le stock » désactivé. À renseigner avant la phase 2.
- Journal des mouvements de stock (entrées/sorties) : prévu avec les commandes (phase 2) ; en attendant, chaque
  modification de stock est tracée dans le journal d'audit.
- Médias stockés sur le disque local (`backend/media/`) ; stockage externe (S3/R2) à brancher à la mise en ligne.

- Limitation de débit stockée en mémoire locale : en production avec plusieurs processus, il faudra un cache partagé (ex. Redis).
- L'IP enregistrée est `REMOTE_ADDR` : derrière un proxy, il faudra configurer la lecture de `X-Forwarded-For`.
- 2FA (TOTP) recommandée pour le rôle Propriétaire : non incluse en phase 0.
