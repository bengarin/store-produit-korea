# Audit de mise en production — 2026-11-03

Audit réalisé **en local uniquement** (base de développement MySQL 8.4 dans Docker). Aucun déploiement, aucun push,
aucun paiement, aucune vraie commande. Aucune donnée supprimée, aucune base réinitialisée.

## Verdict

**PRÊT SOUS RÉSERVE DE CORRECTIONS.** Le code et les tests sont en bon état. La mise en ligne est bloquée par des
éléments **hors code** : informations légales, SMTP, serveur VPS, sauvegardes externes, stock réel, relecture juridique.

## 1. Modifications faites pendant l'audit

| Fichier | Modification | Pourquoi | Preuve |
|---|---|---|---|
| `backend/apps/inventory/views.py` | Images des produits préchargées (`Prefetch` `gallery_images`) | La page Stock faisait 1 requête SQL de plus **par produit** (N+1) | 12 → 8 requêtes, fixe quel que soit le nombre de produits |
| `backend/tests/test_query_counts.py` (nouveau) | Test : même nombre de requêtes avec 2 ou 8 produits (Stock, Produits admin, catalogue public) | Empêcher le retour du N+1 | Passe ; échoue sur l'ancien code |
| `package.json`, `package-lock.json` | `react-router-dom` 6.x → **7.18.5** (version exacte) | 2 alertes de sécurité « moderate » sur react-router | `npm audit` : alertes react-router disparues |
| `docs/BLUEHOST.md` | Précision : AlmaLinux 8/9/10 au choix ; version MySQL non indiquée par Bluehost | Vérifié sur le site Bluehost le 2026-11-03 | — |

Effet visible de react-router 7 : les liens portent un attribut `data-discover="true"` (aucun effet visuel), et les
changements d'onglet passent par une transition React (contenu affiché au rendu suivant). Le bundle principal passe
de 93,65 à 100,77 kB gzip (+7 kB).

## 2. Résultats des tests (réels, 2026-11-03)

| Test | Résultat |
|---|---|
| Backend pytest | **404 / 404** réussis (81 s) |
| ruff check + format | OK, 194 fichiers |
| ESLint (`--max-warnings=0`) | OK |
| Build Vite (démo + API) | OK |
| Contrat API (démo ↔ serveur) | 0 différence |
| Validateurs de thème | 37 cas, 0 écart |
| DOM démo vs référence (FR/AR, 360 → 1366 px) | identique, sauf 8 écarts mobiles **attendus** (nouvel ordre de la fiche produit mobile) |
| Fiche produit ordinateur avant/après | 40 / 40 identiques |
| E2E : mobile, Meta Pixel, arabe, contenus arabes, visuels marketing, variantes, constructeur produit, thèmes, admin | tous « TOUT OK » |
| E2E tableau de bord | OK (après correction du **script de test** : attendre la sélection de l'onglet) |
| CSP navigateur | 0 violation |
| Journal Django pendant les tests | 4 699 requêtes, **0 erreur 5xx** |
| `check --deploy` (réglages prod) | 0 problème (1 masqué : HSTS preload volontairement désactivé) |
| pip-audit | 0 vulnérabilité |
| npm audit | restent 2 alertes **outils de dev uniquement** (esbuild via Vite ≤ 6 ; minimatch via ESLint) — non embarquées dans le site |
| Sauvegarde → restauration (base neuve `mpc_verif_audit`) | 47 tables, 4 011 lignes, empreintes identiques |
| MySQL (lecture) | 47 tables InnoDB utf8mb4, 51 clés étrangères toutes indexées, 60 contraintes CHECK |

Non testable ici : Safari/iOS réel, envoi Meta réel (domaines bloqués dans le bac à sable), e-mails réels (pas de SMTP).

## 3. Sécurité

Contrôlé : aucun `.env` versionné ; aucun secret dans l'historique Git (2 mots de passe trouvés = valeurs de test
factices) ; la prod refuse de démarrer sans `DJANGO_SECRET_KEY` (≥ 40 car.) et `DJANGO_ALLOWED_HOSTS` ; HTTPS forcé,
cookies `Secure`, HSTS, ~~2FA obligatoire owner/admin~~ (retirée le 3 nov. 2026 à la demande du propriétaire) ; CSP stricte ; admin = 403 sans session ; injection SQL dans les
filtres sans effet (ORM, tri en liste blanche) ; HTML riche nettoyé côté serveur (nh3) et navigateur ; commande sans
clé d'idempotence refusée. Détails : `docs/SECURITY_AUDIT.md`.

## 4. Parcours e-commerce (18)

| # | Parcours | État |
|---|---|---|
| 1 | Navigation boutique | ✅ testé |
| 2 | Recherche et filtres | ⚠️ filtres catégorie / favoris / ingrédient OK — **pas de recherche texte** |
| 3 | Fiches produit | ✅ |
| 4 | Galerie + visuels marketing | ✅ |
| 5 | FR / AR (RTL) | ✅ — contenus produits arabes **à saisir** |
| 6 | Panier, quantités | ✅ |
| 7 | Validation commande | ✅ |
| 8 | Création de commande | ✅ (commandes de test locales uniquement) |
| 9 | Statuts de commande | ✅ tests backend |
| 10 | Clients | ✅ |
| 11 | Produits | ✅ |
| 12 | Stock | ✅ — **stock réel non saisi** |
| 13 | Images | ✅ (WebP 1 600 + 640 px) |
| 14 | Frais de livraison | ✅ tests backend (zones / villes) — **tarifs réels à confirmer** |
| 15 | E-mails / notifications | ⚠️ code testé ; **SMTP non configuré** |
| 16 | Administration (5 rôles) | ✅ |
| 17 | Meta Pixel + consentement | ✅ local ; **à valider dans Events Manager** |
| 18 | Pages légales / confidentialité | ⚠️ pages présentes ; **mentions légales vides**, pas de validation juridique |

## 5. Ce qui reste avant la mise en ligne

| Priorité | Point |
|---|---|
| CRITIQUE | Mentions légales réelles (raison sociale, ICE, RC, IF, adresse) + relecture juridique (loi 09-08, CNDP) |
| CRITIQUE | Serveur : VPS auto-géré (le mutualisé n'est pas adapté à Django), domaine, certificat HTTPS |
| CRITIQUE | Variables de production : clé secrète, hôtes, `SITE_URL` en HTTPS, cache partagé (`createcachetable`) |
| ÉLEVÉE | SMTP transactionnel (SPF/DKIM) |
| ÉLEVÉE | Sauvegardes automatiques **hors du serveur** + test de restauration mensuel |
| ÉLEVÉE | Base de production propre : sans commandes de test, code promo démo `NATURE10`, comptes `@exemple.ma` (`launch_check` les signale) |
| ÉLEVÉE | Stock réel et tarifs de livraison réels |
| MOYENNE | Vérifier sur emballage les mentions des visuels marketing (`docs/VISUELS_MARKETING.md`) |
| MOYENNE | Supervision (uptime, logs, alertes) ; test Safari/iOS réel |
| FAIBLE | Recherche texte ; LCP accueil ~5,4 s en 4G lente simulée ; pagination du catalogue public (inutile à 5 produits) ; Vite 8 (outil de dev) |

Commande de contrôle avant ouverture : `python manage.py launch_check` (doit afficher « PRÊT »).
