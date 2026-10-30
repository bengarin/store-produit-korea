# Backend — Ma Petite Corée (Django + DRF + MySQL)

Phase 0 (fondations) : configuration, comptes de l'équipe et 5 rôles, connexion sécurisée,
journal d'audit, format d'erreur commun, `/api/v1/health`, tests et lint.
Aucun produit, commande ou écran d'administration pour l'instant (phases suivantes, voir `docs/ARCHITECTURE.md`).

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

# 6. Lancer l'API
python manage.py runserver
#    → http://127.0.0.1:8000/api/v1/health
```

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

## API disponible (phase 0)

| Méthode | Route | Accès | Réponse |
|---|---|---|---|
| GET | `/api/v1/health` | public | `{"status":"ok","database":"ok","version":"0.1.0"}` ou 503 |
| GET | `/api/v1/admin/auth/csrf` | public | dépose le cookie `mpc_csrftoken`, renvoie `{"csrfToken"}` |
| POST | `/api/v1/admin/auth/login` | public + en-tête `X-CSRFToken` | `{"user": {...}, "csrfToken"}` + cookie `mpc_session` (HttpOnly) |
| POST | `/api/v1/admin/auth/logout` | connecté + CSRF | 204 |
| GET | `/api/v1/admin/auth/me` | membre de l'équipe | `{"user": {id, email, firstName, lastName, role, roleLabel}}` |
| POST | `/api/v1/admin/auth/password` | membre + CSRF | `{currentPassword, newPassword}` → 204 |

Erreurs (toujours le même format) :
```json
{"error": {"code": "validation_error", "message": "Certaines informations sont invalides.", "fields": {"email": ["…"]}}}
```
Codes : `validation_error`, `parse_error`, `not_authenticated`, `authentication_failed`, `permission_denied`,
`csrf_failed`, `account_locked`, `not_found`, `method_not_allowed`, `throttled`, `service_unavailable`, `server_error`.

## Sécurité en place

- Session Django (cookie `HttpOnly`, `SameSite=Lax`, 8 h, `Secure` en prod) + CSRF obligatoire, y compris sur la connexion.
- Mots de passe hachés en Argon2, 12 caractères minimum, mots de passe courants refusés.
- Verrouillage après 5 échecs (e-mail + IP, 1 h) — django-axes ; limitation de débit sur la connexion.
- Message d'échec identique que le compte existe ou non ; nouvelle session à chaque connexion.
- Journal d'audit en ajout seul : connexions, échecs, verrouillages, déconnexions, changements de mot de passe, création d'utilisateurs. Les mots de passe et jetons sont masqués automatiquement.
- Aucun secret dans le dépôt : `backend/.env` est ignoré par git.

## Limites connues (à traiter plus tard)

- Limitation de débit stockée en mémoire locale : en production avec plusieurs processus, il faudra un cache partagé (ex. Redis).
- L'IP enregistrée est `REMOTE_ADDR` : derrière un proxy, il faudra configurer la lecture de `X-Forwarded-For`.
- 2FA (TOTP) recommandée pour le rôle Propriétaire : non incluse en phase 0.
