# Audit de sécurité — Phase 7 (2 novembre 2026)

Périmètre : backend Django 5.2 / DRF, admin React, boutique publique, configuration de production
(`deploy/`), scripts d'exploitation (`scripts/ops/`). Base de départ : commit `c173449`.

Méthode : lecture du code, tests d'attaque automatisés (`backend/tests/test_security.py`), vrai déploiement local
nginx 1.24 + gunicorn 26 avec certificat de test, Chromium sous CSP, `pip-audit`, `npm audit`, `ruff --select S`
(règles de sécurité Bandit), recherche de secrets dans tout l'historique Git.

Limites : **pas de test d'intrusion externe**, pas de test Safari (WebKit indisponible ici), pas de serveur Bluehost
réel. Ce rapport ne remplace pas un audit professionnel. [NON VÉRIFIÉ] en conditions réelles d'hébergement.

## 1. Failles trouvées et corrigées

| # | Gravité | Problème (démontré) | Correction | Preuve |
|---|---------|---------------------|------------|--------|
| 1 | **Haute** | Les limites anti-abus (connexion, commandes, codes promo, newsletter) se contournaient en envoyant un faux en-tête `X-Forwarded-For` différent à chaque requête. | `TrustedProxyMiddleware` : l'IP vient de `REMOTE_ADDR`, ou de la n-ième adresse en partant de la droite de `X-Forwarded-For` seulement si `TRUSTED_PROXY_COUNT=n` ; nginx **remplace** l'en-tête. | `test_limites_de_debit_insensibles_a_un_x_forwarded_for_forge`, `test_ip_reelle_derriere_proxy_de_confiance` ; test réel nginx : 10 essais puis 429, malgré 12 IP forgées. |
| 2 | **Haute** | Avec plusieurs processus gunicorn, chaque processus avait son propre cache mémoire : les limites anti-abus étaient **multipliées par le nombre de processus** (constaté : 11 essais acceptés au lieu de 10 avec 2 processus). | Production : cache partagé `DatabaseCache` (table MySQL `mpc_cache`, `manage.py createcachetable`). Vérifié par `launch_check`. | Même test réel après correction : 10 essais puis 429 ; `test_production_check_deploy_sans_avertissement` vérifie le cache. |
| 3 | **Haute** | Pillow 11.x : 39 vulnérabilités connues (traitement d'images envoyées depuis l'admin). | Pillow 13.0.0. | `pip-audit` : 0 vulnérabilité ; les 118 tests images passent. |
| 4 | Moyenne | Aucun second facteur : un mot de passe volé = accès complet (commandes, données clients). | 2FA TOTP standard (django-otp, RFC 6238), 10 codes de secours à usage unique, obligatoire en production pour Propriétaire/Admin, refus de rejouer un code, ralentissement après un échec, limite `otp` 10/min. | 6 tests 2FA + parcours navigateur complet (QR décodé par un vrai lecteur). |
| 5 | Moyenne | Pas de moyen de fermer les sessions d'un compte compromis. | Bouton « Fermer les autres sessions », commandes `revoke_sessions` (option `--deactivate`) et `reset_2fa`. Un changement de mot de passe ferme les autres sessions. | `test_revocation_des_sessions_et_recuperation_de_compte`, `test_changement_de_mot_de_passe_ferme_les_autres_sessions`. |
| 6 | Basse | Exemple nginx : un nom de domaine inconnu (Host forgé) recevait la page d'accueil par défaut de nginx. | Serveurs `default_server` : `return 444` + `ssl_reject_handshake on`. | Test réel : connexion fermée (000) pour Host et SNI inconnus. |
| 7 | Basse | Exemple nginx initial incompatible avec nginx < 1.25 (`http2 on;`), alors qu'AlmaLinux 9 fournit 1.20 à 1.24. | `listen 443 ssl http2;`. | `nginx -t` OK sur 1.24. |
| 8 | Basse | Fichiers envoyés : un fichier non-image dans `/media/` aurait pu être servi comme page HTML. | nginx : `/media/` refuse `.html/.svg/.php/…`, `nosniff`, CSP `sandbox`. (Django n'accepte déjà que des images vérifiées par Pillow.) | Test réel : `/media/x.html` → 403. |

Bug fonctionnel trouvé pendant l'audit : le QR code 2FA ne s'affichait pas (SVG sans `xmlns`). Il est corrigé et
vérifié dans le navigateur.

## 2. Points vérifiés sans problème

- **Authentification admin** : session Django + CSRF, cookie de session `HttpOnly`, `Secure` (production), `SameSite=Lax`, durée 8 h, mots de passe Argon2, verrouillage django-axes (5 échecs par couple e-mail + IP, 1 h).
- **Permissions** : toutes les routes `/api/v1/admin/*` refusent les visiteurs (test qui parcourt automatiquement toutes les routes). L'éditeur de contenu n'a aucun accès aux données personnelles (commandes, clients, factures, e-mails). Coût d'achat jamais exposé publiquement.
- **Production** : refuse de démarrer sans `DJANGO_SECRET_KEY` (40 caractères minimum) ni `DJANGO_ALLOWED_HOSTS` ; `DEBUG` forcé à False ; `check --deploy` sans avertissement ; HTTPS forcé (301) ; HSTS 30 jours.
- **En-têtes** (mesurés derrière nginx) : CSP `script-src 'self'` sans script en ligne, `frame-ancestors 'self'`, `X-Frame-Options` (`DENY` pour l'API, `SAMEORIGIN` pour les pages, nécessaire à l'aperçu du thème), `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy`, `nosniff`. Chromium : 0 violation CSP sur la boutique, l'admin et l'aperçu du thème.
- **Injection** : ORM uniquement (aucun SQL brut construit avec des données reçues) ; HTML produit assaini par nh3 ; noms de produit piégés (`</script>…`) échappés dans le HTML servi et le JSON-LD (test) ; e-mails en texte brut ; factures échappées (test).
- **Thème** : aucun HTML/JS/CSS arbitraire, validation identique côté JS et Python (cas partagés).
- **Redirection après connexion** : `?next=` limité à `/admin/…` (pas de `//`, pas de `\`).
- **Secrets** : aucun fichier `.env` suivi par Git ; aucun secret réel dans l'historique (seuls des mots de passe de test fictifs dans `tests/`) ; `.env.example` ne contient que des valeurs vides ou fictives ; l'écran « E-mails » de l'admin n'affiche aucun mot de passe SMTP (test).
- **Sauvegardes** : mot de passe MySQL jamais en ligne de commande (`--defaults-extra-file`), fichiers créés en `umask 077`, empreintes SHA-256, restauration refusée vers une base existante.
- **Analyse statique** : `ruff --select S` : 0 alerte (exceptions justifiées et commentées dans le code).

## 3. Risques restants (non corrigés — à décider)

| Risque | Niveau | Pourquoi non corrigé | Recommandation |
|--------|--------|----------------------|----------------|
| `react-router-dom` 6.30.6 : 2 alertes « modérées » (`npm audit`). | Faible ici | 1) Redirection ouverte via `\` : notre seul `next` piloté par l'utilisateur est filtré (`safeNext`). 2) `deserializeErrors` : uniquement en rendu serveur React, que nous n'utilisons pas. La correction impose la v7 (changement majeur). | Migrer vers react-router 7 dans une phase dédiée, avec les tests de non-régression. |
| Formulaire de commande public : pas de CAPTCHA. | Moyen | Limites existantes : 10 commandes/h par IP + nombre de commandes par téléphone sur 1 h (compté en base). Un CAPTCHA tiers ajoute un service externe et du suivi. | Surveiller les 2 premières semaines ; ajouter un CAPTCHA (ex. Cloudflare Turnstile) si du spam apparaît. |
| Protection DDoS / pare-feu applicatif. | Moyen | Hors du code : dépend de l'hébergeur. | Mettre Cloudflare (offre gratuite) devant le site ; dans ce cas `TRUSTED_PROXY_COUNT` doit être recalculé (voir `PRODUCTION.md`). |
| Sauvegardes sur le même serveur. | **Élevé** si non traité | Une copie hors serveur exige un stockage choisi par le propriétaire. | Copier chaque nuit le dossier de sauvegarde ailleurs (stockage S3/Backblaze, ou serveur distinct). **Bloquant pour l'ouverture.** |
| Mises à jour de sécurité du serveur (VPS). | Élevé | Sur un VPS non géré, c'est l'exploitant qui patche le système. | `dnf-automatic` pour les correctifs de sécurité + revue mensuelle `pip-audit` / `npm audit`. |
| Journal des accès admin / alertes de connexion. | Faible | Le journal d'audit existe (actions admin) ; pas d'alerte e-mail à la connexion. | Optionnel après ouverture. |

## 4. Verdict

Aucune faille connue ouverte dans le code testé. La sécurité **en production** dépend encore de points non
vérifiables ici : configuration réelle du serveur, copie des sauvegardes hors serveur, certificat HTTPS,
mises à jour système. → [NON VÉRIFIÉ] tant que ces points ne sont pas faits sur le vrai serveur.
