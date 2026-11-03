# Compatibilité Bluehost — analyse (2 novembre 2026)

> Basée sur la documentation publique de Bluehost (liens en bas). **Aucun serveur Bluehost n'a été testé.**
> L'offre réellement souscrite par le propriétaire est inconnue → [DONNÉES MANQUANTES].

## 1. Ce que l'application exige (mesuré)

| Exigence | Pourquoi |
|----------|----------|
| Python **≥ 3.11** | Pillow 13 (correctif de 39 failles) l'exige ; testé en 3.11 et 3.13 |
| Processus Python permanent (gunicorn) + relais web (nginx/Apache) | Django n'est pas du PHP |
| MySQL 8.x (testé 8.4), utf8mb4 | base de données |
| Tâches planifiées (cron) | e-mails en attente, sessions, sauvegardes |
| Accès SSH | installation, migrations, récupération de compte (`reset_2fa`…) |
| HTTPS (certificat) | cookies `Secure`, HSTS |
| ~1 Go de RAM minimum conseillé [HYPOTHÈSE] | MySQL + 3 processus gunicorn |

## 2. Offres Bluehost

| Offre | Verdict | Raisons |
|-------|---------|---------|
| **Mutualisé** (Basic/Choice Plus…) | ❌ Non recommandé | Pensé pour PHP/WordPress ; pas de processus Python permanent garanti ; pas de root ; version de Python non maîtrisée (communication Bluehost : 3.9 à 3.11 selon serveurs) [NON VÉRIFIÉ sur votre compte]. Même si un « Python App » via Passenger existait, Pillow 13 exige 3.11+. |
| **VPS (auto-géré)** | ⚠️ Faisable | AlmaLinux (8, 9 ou 10 au choix selon la page Bluehost consultée le 2026-11-03 ; 9 testé dans ce guide), accès root SSH ; MySQL non fourni en version précise par Bluehost [NON VÉRIFIÉ] ; on installe soi-même Python 3.11/3.12, MySQL 8.4 (dépôt officiel MySQL), nginx, certbot. Bluehost indique ne **pas** installer Django lui-même : l'exploitation (mises à jour, sécurité, sauvegardes) est à votre charge. |
| **Dédié** | ⚠️ Faisable mais surdimensionné | Même chose que le VPS, plus cher. |

**Lieu du serveur** : choisir **Frankfurt** (centre de données VPS autogéré annoncé par Bluehost, le plus proche du Maroc) ; il ne peut plus être changé après la création. Héberger hors du Maroc = transfert de données personnelles à l'étranger : vérifier l'autorisation CNDP (voir `PREPARATION_MISE_EN_LIGNE.md`).

**Recommandation** : VPS uniquement, et seulement si quelqu'un peut administrer un serveur Linux (mises à jour
mensuelles, surveillance, restauration). Sinon, une plateforme gérée pour Python (ex. un PaaS) réduit le risque
d'exploitation — à comparer sur prix et localisation [NON VÉRIFIÉ, comparatif non fait].

## 3. À vérifier sur l'offre réelle avant tout déploiement

1. Type d'offre exact (mutualisé / VPS / dédié) et capacité (RAM, CPU, disque).
2. Système : `cat /etc/os-release` ; Python disponible : `dnf list 'python3.1*'` (besoin de 3.11 ou 3.12).
3. Accès root SSH effectif.
4. cPanel/WHM présent ? (Il gère Apache : il faudrait alors adapter `deploy/nginx.conf.example` en configuration Apache *reverse proxy*, ou désactiver le relais web de cPanel.)
5. MySQL : version installable (8.4 visé) ; ne pas utiliser MariaDB sans nouveaux tests.
6. Ports 80/443 ouverts, DNS du domaine modifiable, certificat Let's Encrypt possible.
7. Sauvegardes Bluehost incluses ou non → la copie externe reste nécessaire (voir `PRODUCTION.md` §7).
8. Envoi d'e-mails : SMTP Bluehost utilisable (port 587 + TLS) ou fournisseur dédié (meilleure délivrabilité) [À DÉCIDER].

## 4. Plan proposé (après votre validation)

1. Vous me donnez l'offre exacte et les réponses aux points 1 à 4.
2. Installation sur le VPS **sous une adresse de test** (sous-domaine non annoncé, `noindex`), base vide.
3. `launch_check` + tests navigateur (dont un vrai iPhone/Safari) sur ce serveur.
4. Saisie des vraies données (mentions légales, stock compté, prix) par vous.
5. Votre **accord écrit** → bascule du domaine public.

## Sources

- https://www.bluehost.com/help/article/vps-dedicated-third-party-applications
- https://www.bluehost.com/help/article/bh-what-to-expect-with-self-managed-vps
- https://www.bluehost.com/blog/vps-hosting-for-developers/
- https://www.bluehost.com/blog/vps-hosting-with-cpanel/
- https://www.bluehost.com/blog/mysql-version/
- https://hostadvice.com/hosting-company/blue-host-reviews/blue-host-django-hosting-review/ (source tierce)
