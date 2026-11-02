# Mise en production — Ma Petite Corée

> **Aucun déploiement public sans l'accord écrit du propriétaire.** Ce document décrit *comment* faire.
> Il ne vaut pas autorisation.

## 1. Architecture cible (un seul serveur)

```
Visiteur ──HTTPS──▶ nginx ──▶ /assets/*, favicons      → fichiers du front construit (dist/)
                         ├─▶ /media/*                  → images envoyées depuis l'admin
                         └─▶ tout le reste             → gunicorn (127.0.0.1:8000) → Django → MySQL 8.4
cron : e-mails en attente (10 min) · nettoyage des sessions (nuit) · sauvegarde (nuit) + copie hors serveur
```

Django sert lui-même les pages HTML (titre, description, Open Graph et JSON-LD injectés par page), le sitemap
et robots.txt. nginx ne sert que les fichiers statiques.

## 2. Prérequis vérifiés

| Élément | Version exigée | Testé ici |
|---------|----------------|-----------|
| Python | **≥ 3.11** (Pillow 13 l'exige ; Django 5.2 : ≥ 3.10) | 3.11.17 (384 tests OK) et 3.13 |
| MySQL | 8.4 LTS (utf8mb4) | 8.4 (Docker) |
| nginx | ≥ 1.19.4 (`ssl_reject_handshake`) | 1.24 |
| Node.js (uniquement pour construire le front) | 20 ou 22 | 22.22 |
| Accès | SSH + droits root (installer Python, nginx, MySQL, systemd, cron) | — |

## 3. Variables d'environnement (fichier `/etc/mpc/production.env`, `chmod 600`, hors Git)

| Variable | Obligatoire | Exemple / remarque |
|----------|-------------|--------------------|
| `DJANGO_SECRET_KEY` | oui | `python -c "import secrets; print(secrets.token_urlsafe(50))"` — l'application refuse de démarrer sans |
| `DJANGO_ALLOWED_HOSTS` | oui | `votre-domaine.ma` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | oui | `https://votre-domaine.ma` |
| `SITE_URL` | oui | `https://votre-domaine.ma` (adresses canoniques, sitemap, Open Graph) |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | oui | utilisateur MySQL dédié, droits sur la seule base de la boutique |
| `MEDIA_ROOT` | oui | `/srv/mpc/media` |
| `FRONTEND_DIST_DIR` | oui | `/srv/mpc/dist` |
| `TRUSTED_PROXY_COUNT` | oui | `1` avec nginx seul ; **voir §8 si Cloudflare** |
| `TWO_FACTOR_REQUIRED_ROLES` | non | défaut production : `owner,admin` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`/`EMAIL_USE_SSL`, `DEFAULT_FROM_EMAIL`, `ORDER_NOTIFICATION_EMAILS` | non | vides = aucun e-mail ne part (tout est journalisé « non envoyé ») |
| `DJANGO_HSTS_PRELOAD` | non | `false` tant que le domaine n'est pas en HTTPS partout |

Le service systemd fixe `DJANGO_SETTINGS_MODULE=config.settings.prod` et `DJANGO_ENV_FILE=none` : le fichier
`backend/.env` n'est **jamais** lu en production.

## 4. Installation (première fois)

```bash
# Système (exemple AlmaLinux 9 — adapter) : python3.11 ou python3.12, nginx, MySQL 8.4 (dépôt officiel MySQL), certbot
sudo useradd --system --home /srv/mpc mpc
sudo -u mpc git clone <dépôt> /srv/mpc/app
sudo -u mpc python3.11 -m venv /srv/mpc/venv
sudo -u mpc /srv/mpc/venv/bin/pip install -r /srv/mpc/app/backend/requirements/prod.txt

# Front (sur le serveur ou sur un poste, puis copie de dist/)
cd /srv/mpc/app && npm ci && VITE_API_BASE_URL=/api/v1/store npm run build && cp -r dist /srv/mpc/dist

# Base : créer la base et l'utilisateur MySQL, puis
ENV_FILE=/etc/mpc/production.env VENV=/srv/mpc/venv scripts/ops/manage.sh migrate
ENV_FILE=/etc/mpc/production.env VENV=/srv/mpc/venv scripts/ops/manage.sh createcachetable
ENV_FILE=/etc/mpc/production.env VENV=/srv/mpc/venv scripts/ops/manage.sh check --deploy
```

Puis copier et adapter `deploy/nginx.conf.example`, `deploy/mpc-gunicorn.service.example` et
`deploy/crontab.example`. Certificat : `certbot --nginx -d votre-domaine.ma -d www.votre-domaine.ma`.

## 5. Données réelles — avant l'ouverture

1. **Ne jamais copier la base de développement** : elle contient des commandes et stocks de test.
2. Base de production vide → `migrate` → créer le compte Propriétaire (`createsuperuser`, puis rôle owner) → la 2FA est demandée dès la 1re connexion.
3. Saisir dans l'admin : mentions légales (raison sociale, adresse, ICE, RC, IF, patente), taux de TVA confirmé par le comptable, coordonnées, zones de livraison, les 5 produits avec **leur stock réel compté**.
4. Lancer la vérification (lecture seule, ne modifie rien) :

```bash
ENV_FILE=/etc/mpc/production.env VENV=/srv/mpc/venv scripts/ops/manage.sh launch_check
```

Elle signale : DEBUG, secret, HTTPS, 2FA, cache partagé, migrations, front, mentions légales, stock non renseigné ou
à 0, prix, produits/commandes/codes promo de test, comptes `@exemple.ma`. Code de sortie 1 tant qu'un point
bloquant reste. 5. Relire **à la main** chaque prix et chaque fiche produit.

## 6. Mise à jour (déploiements suivants)

```bash
cd /srv/mpc/app && git fetch && git checkout <version validée>
/srv/mpc/app/scripts/ops/backup.sh                       # 1. sauvegarde AVANT toute mise à jour
/srv/mpc/venv/bin/pip install -r backend/requirements/prod.txt
M="env ENV_FILE=/etc/mpc/production.env VENV=/srv/mpc/venv scripts/ops/manage.sh"
$M makemigrations --check --dry-run                       # 2. doit dire « No changes detected »
$M migrate --plan                                         # 3. lire la liste : aucune suppression de table/colonne inattendue
$M migrate
$M check --deploy
npm ci && VITE_API_BASE_URL=/api/v1/store npm run build && rsync -a --delete dist/ /srv/mpc/dist/
sudo systemctl restart mpc-gunicorn
$M launch_check
```

Retour arrière : `git checkout <version précédente>` + redémarrage. Si une migration a été appliquée, restaurer
la sauvegarde de l'étape 1 dans une **nouvelle** base (§7) plutôt que d'annuler les migrations à la main.

## 7. Sauvegarde, restauration, reprise après incident

**Sauvegarde** (`scripts/ops/backup.sh`, chaque nuit par cron) : `mysqldump --single-transaction` (sans bloquer la
boutique) + archive des médias + empreintes SHA-256. Le mot de passe est lu dans un fichier d'options MySQL
`chmod 600` (`MYSQL_CNF`), jamais sur la ligne de commande. `RETENTION_DAYS=30` ne supprime que les anciennes
**sauvegardes**.

**Copie hors serveur — obligatoire** : une sauvegarde restée sur le serveur disparaît avec lui. Copier chaque
nuit `/srv/mpc/backups` vers un stockage externe (choix du propriétaire, ex. rclone vers Backblaze B2 / S3).
[DONNÉES MANQUANTES : stockage à choisir].

**Restauration** (testée le 2 novembre 2026, 46 tables, empreintes identiques) :

```bash
MYSQL_CNF=/etc/mpc/restore.cnf scripts/ops/restore.sh /srv/mpc/backups/AAAAMMJJ-HHMMSS mpc_restauration /srv/mpc/media_restauration
DB_NAME=mpc_restauration ... manage.py verify_backup --against mapetitecoree   # comparaison table par table (lecture seule)
```

Le script **refuse** une base cible existante et un dossier médias non vide : rien n'est jamais écrasé. Pour
basculer : arrêter gunicorn, changer `DB_NAME` (et `MEDIA_ROOT`), redémarrer, lancer `launch_check`.

**Incidents courants**

| Situation | Action |
|-----------|--------|
| Serveur perdu | Nouveau serveur (§4) → restaurer la dernière copie externe → `launch_check` → DNS. Perte maximale : 24 h de commandes (sauvegarde nocturne). |
| Base corrompue / erreur humaine | Restaurer dans une nouvelle base, comparer, basculer. Ne jamais restaurer par-dessus. |
| Compte admin compromis | `manage.py revoke_sessions --email X --deactivate`, puis `changepassword X`, `reset_2fa --email X`, réactiver. |
| Téléphone 2FA perdu | Se connecter avec un code de secours ; sinon un autre Propriétaire/Admin, ou en SSH : `manage.py reset_2fa --email X` (ferme ses sessions). |
| Mot de passe oublié | En SSH : `manage.py changepassword X` (il n'y a pas de réinitialisation par e-mail : choix volontaire tant que l'e-mail n'est pas configuré). |
| E-mails non reçus | Admin → Paramètres → E-mails (état, dernier échec, envoi de test) ; `send_pending_emails` les renvoie. |

## 8. Points d'attention

- **`TRUSTED_PROXY_COUNT`** = nombre de relais qui **remplacent** `X-Forwarded-For`. nginx seul : `1`. Avec Cloudflare devant nginx : utiliser le module `real_ip` de nginx avec la liste d'IP officielle de Cloudflare et garder `1`. Une valeur fausse rend les limites anti-abus contournables.
- **Cache partagé** : `createcachetable` est obligatoire (sinon les limites anti-abus sont multipliées par le nombre de processus). `launch_check` le vérifie.
- **CSP** : le build Vite ne contient aucun script en ligne. Ne pas ajouter de script tiers (pixel, chat…) sans adapter `STOREFRONT_CSP`.
- **Liste publique des produits non paginée** : mesuré 1,5 Mo / 0,4 s à 511 produits. Sans effet avec 5 produits ; à paginer au-delà d'environ 100 produits.
- **Image d'accueil** : en 4G lente simulée, la plus grande image s'affiche en ~5,4 s (seuil « bon » de Google : 2,5 s). Piste : précharger l'image du thème publié ou alléger les 197 Ko. Non modifié dans cette phase.
- **Safari / iOS** : non testé (WebKit indisponible dans l'environnement de test). À tester sur un vrai iPhone avant l'ouverture.

## 9. Mesures de performance (2 novembre 2026)

Base séparée `mpc_perf` : 511 produits, 20 060 commandes, 40 084 lignes (la base de développement n'a pas été touchée).

| Requête | Médiane | Requêtes SQL |
|---------|---------|--------------|
| API liste produits (511) | 381 ms (1,5 Mo) | 7 |
| Fiche produit (API / HTML serveur) | 13 ms | 7 / 8 |
| sitemap.xml (511 produits) | 344 ms | 8 |
| Admin : liste des commandes / recherche / détail | 12 / 27 / 14 ms | 7 / 7 / 9 |
| Admin : stock | 62 ms | 32 |
| Admin : tableau de bord 30 j / 12 mois | 1,06 s / 0,84 s | 35 |
| Admin : export Excel de 20 060 commandes | 2,2 s (545 Ko) | 7 |

Navigateur (Chromium mobile 390 px, derrière nginx avec gzip et HTTP/2, données réelles) :

| Page | Réseau rapide : LCP | 4G lente simulée (1,6 Mb/s, 150 ms) : FCP / LCP | Poids |
|------|---------------------|---------------------------------------------------|-------|
| Accueil | 0,30 s | 1,2 s / 5,4 s | 0,9–1,2 Mo |
| Nos produits | 0,22 s | 1,4 s / 2,8 s | 0,45 Mo |
| Fiche produit | 0,23 s | 1,5 s / 2,7 s | 0,5 Mo |

Décalage de mise en page (CLS) ≤ 0,034 partout (seuil « bon » : 0,1). JavaScript principal : 82 Ko gzip ;
admin chargé à part (lazy).
