# Préparation de la mise en ligne — 2026-11-03

Travail **local uniquement**. Aucune donnée supprimée, aucun déploiement, aucun DNS modifié.

## 1. Données de test de la base de développement (inventaire, rien supprimé)

Le site n'a jamais été public : **aucune donnée client réelle**. Tout ce qui suit vient des tests.

| Élément | Quantité | Comment c'est identifié | Supprimable ? |
|---------|----------|-------------------------|---------------|
| Commandes | 82 (4 août → 3 nov. 2026 ; la 82ᵉ, « Test Arabe Pixel », créée par un test navigateur pendant cette préparation) : 23 en attente, 22 confirmées, 4 expédiées, 23 livrées, 8 annulées, 2 retournées | clients « Test… » / « Client… », 37 passées par un navigateur automatisé, 39 contiennent un produit `test-` | Oui, avec leurs 99 lignes et 194 historiques (0 facture) |
| Clients | 43 | noms « Test » (25) et « Client » (18), aucun e-mail | Oui, après les commandes |
| Mouvements de stock | 199 (106 sur produits test, 93 sur les 5 vrais produits) | inventaires, casse, réassort, commandes de test | **Non par conception** : journal en « ajout seul » |
| Stocks actuels des vrais produits | Baroness 28, ORJENA 21, autres 0 | résultat des tests, **pas un comptage réel** | À recompter avant ouverture |
| Produits de test | 21 archivés (36 variantes, 5 utilisées dans des commandes) | slug `test-…` | Oui, après les commandes qui les citent |
| Comptes administration | 5 (`@exemple.ma`, un par rôle) | domaine d'exemple | À remplacer par de vrais comptes |
| Inscrits newsletter | 8 (`@exemple.ma`) | domaine d'exemple | Oui |
| Code promo `NATURE10` (−10 %), utilisé 4 fois | 1 | marqué `[DÉMO]` dans `src/config/store.js` | Désactiver ou garder : à décider |
| Livraison : zone « Maroc » 20 DH, 20 villes | 1 zone | marqué `[DÉMO]` | **À remplacer par vos tarifs** |
| Versions de thème | 44 | tests de l'éditeur visuel | Inutile de supprimer |
| Journal d'audit | 1 558 lignes | actions des tests | À conserver (traçabilité) |
| Base `mpc_verif_audit` | copie restaurée du 3 nov. | test de restauration | Oui, **sur votre accord** |

**Recommandation : ne pas nettoyer la base de développement, démarrer la production avec une base NEUVE.**
Plus sûr (aucune donnée de test ne peut passer en production) et plus simple (le journal de stock ne se supprime pas) :

1. base vide + `migrate` ;
2. `createcachetable` ;
3. `import_store_config` puis vos vrais tarifs de livraison ;
4. `import_catalog` ;
5. vos comptes avec `create_staff_user` ;
6. saisie des prix et des stocks réels dans l'administration ;
7. `launch_check` doit répondre « PRÊT ».

## 2. Vérifications e-commerce

| Point | État | Détail |
|-------|------|--------|
| 6 fiches produits | ✅ prêtes (aperçu validé) | Voir `CATALOGUE_6_PRODUITS.md` |
| Catégories | ✅ | Hydratation, Anti-âge, Éclat ; noms arabes vides |
| Stocks | ❌ | Valeurs de test ; nouveau produit « non renseigné » |
| Prix | ⏳ À définir | Les produits restent en brouillon tant que le prix vaut 0 |
| Frais de livraison | ⚠️ `[DÉMO]` | 20 DH partout, pas de seuil de gratuité, pas de délai |
| Panier, validation, statuts, paiement à la livraison | ✅ testés | Tests automatiques backend + navigateur (audit du 3 nov.) |
| Confirmation client | ✅ **décision : téléphone / WhatsApp** (pas d'e-mail) | Fiche commande (admin) → bouton « WhatsApp » : message pré-rempli (articles, total à payer à la livraison, adresse, demande « OUI »), envoyé à la main par l'admin. Numéros enregistrés au format +212 (82/82 commandes) |
| Notification administrateur | ⚠️ prête, mais SMTP non configuré | Part dès que `EMAIL_HOST`, `DEFAULT_FROM_EMAIL` et `ORDER_NOTIFICATION_EMAILS` sont remplis |
| Pages légales | ❌ | Seule « Confidentialité » existe (voir § 4) |
| Français / arabe | ⚠️ | Interface traduite ; contenus produits arabes non saisis |

**Parcours de commande de test (sans paiement, sans vraie commande)**, à refaire sur la production avant l'ouverture :

1. mettre un produit en Actif avec un prix et un stock de 1 ;
2. ajouter au panier, modifier la quantité, aller jusqu'à la commande ;
3. vérifier les erreurs (téléphone invalide, ville vide) ;
4. commander avec le nom « TEST — ne pas livrer » et votre propre téléphone ;
5. vérifier : numéro reçu, stock passé à 0, e-mail administrateur reçu, commande visible dans l'administration ;
6. passer la commande en « Annulée » : le stock revient à 1 ;
7. laisser cette commande annulée (traçabilité) et remettre le stock réel.

## 3. Sauvegarde et sécurité

- **Automatique** : `scripts/ops/backup.sh` chaque nuit à 02:41. Il sauvegarde MySQL et les médias, avec empreintes SHA-256, et garde 30 jours.
- **Externe (nouveau)** : `scripts/ops/offsite.sh` chaque nuit à 03:11.
  - Il copie la dernière sauvegarde **hors du serveur** avec rclone (destination chiffrée, par exemple Backblaze B2 ou S3), puis relit la copie.
  - Il refuse d'envoyer une sauvegarde abîmée.
  - Testé ici avec un faux rclone. [NON TESTÉ avec un vrai fournisseur.]
  - Fournisseur à choisir : [DONNÉES MANQUANTES].
- **Restauration testée** le 3 nov. 2026 : 47 tables et 4 011 lignes identiques (`restore.sh` vers une base séparée, puis `verify_backup`). À refaire chaque mois.
- **Secrets** : `.env` jamais versionné ; la production refuse de démarrer sans clé secrète (40 caractères minimum) et sans domaine. Mot de passe MySQL lu depuis un fichier `chmod 600`.
- **HTTPS** : redirection obligatoire, cookies `Secure`, HSTS, CSRF, CSP stricte. CORS sans objet : même domaine.
- **Médias** : réencodés en WebP, scripts et SVG refusés, servis en « sandbox ». Les fichiers cachés (`.env`, `.git`) sont bloqués par nginx (règle ajoutée).
- **Permissions** : 5 rôles, double authentification obligatoire pour Propriétaire et Admin.

## 4. Informations légales à fournir (rien n'est inventé)

| Donnée | Où elle sert | Statut |
|--------|--------------|--------|
| Raison sociale, forme juridique, capital | Mentions légales, factures | [DONNÉES MANQUANTES] |
| Adresse du siège | Mentions légales, factures, CGV | [DONNÉES MANQUANTES] |
| ICE, RC (ville + numéro), IF, patente | Mentions légales, factures | [DONNÉES MANQUANTES] |
| Taux de TVA (ou non-assujettissement) | Factures | [DONNÉES MANQUANTES] |
| Directeur de la publication, e-mail et téléphone de contact | Mentions légales | [DONNÉES MANQUANTES] |
| Hébergeur (nom, adresse) | Mentions légales | Après le choix du serveur |
| Récépissé de déclaration CNDP (loi 09-08) | Politique de confidentialité | [DONNÉES MANQUANTES] |
| Autorisation CNDP de transfert à l'étranger (hébergement hors Maroc, Meta Pixel) | Confidentialité | [À VÉRIFIER par un juriste] |
| Délais et zones de livraison, tarifs, seuil de gratuité | Politique de livraison, CGV | [DONNÉES MANQUANTES] |
| Retours : délai de rétractation (loi 31-08 : 7 jours selon les sources consultées), état exigé, frais, mode de remboursement en paiement à la livraison | Politique de retour | [À VÉRIFIER par un juriste] |
| Produits exclus du retour (hygiène, produit ouvert ?) | Politique de retour | [À VÉRIFIER par un juriste] |

Pages à créer quand les données seront fournies : **mentions légales, CGV, livraison, retours et remboursement**. La politique de confidentialité existe déjà, mais n'a pas été validée par un juriste.

## 5. Hébergement Bluehost (rien commandé)

| Brique | Compatible VPS AlmaLinux | Remarque |
|--------|---------------------------|----------|
| React / Vite | ✅ | Fichiers statiques servis par nginx |
| Django / DRF | ✅ | gunicorn + systemd (`deploy/`) |
| MySQL 8.4 | ✅ à installer soi-même | Version non fournie par Bluehost [NON VÉRIFIÉ] |
| AlmaLinux 8, 9 ou 10 | ✅ | Choix au déploiement ; guide testé en 9 |
| nginx + HTTPS (Let's Encrypt) | ✅ | Gratuit ; renouvellement automatique |
| Domaine | ⚠️ | DNS à faire pointer vers le serveur (non modifié) |
| Médias | ✅ disque du VPS | À sauvegarder (inclus dans `backup.sh`) |
| E-mails transactionnels | ⚠️ | Utiliser un service SMTP externe (Brevo, Mailgun, SES…) + SPF/DKIM : envoyer directement depuis un VPS finit souvent en spam |
| Sauvegardes | ✅ local + ⚠️ externe à configurer | `offsite.sh` |
| Logs et surveillance | ⚠️ | journald + `/var/log/mpc` ; surveillance externe de `/api/v1/health` à ajouter (ex. UptimeRobot) |
| Déploiement et retour arrière | ✅ documentés | `docs/PRODUCTION.md` |
| **Mutualisé** | ❌ | Non adapté à Django |

- **Lieu du serveur** : Bluehost propose Frankfurt pour les VPS autogérés. C'est le centre le plus proche du Maroc, à choisir au déploiement, et il ne pourra plus être changé ensuite.
- **Coûts** [NON VÉRIFIÉ, sources contradictoires] :
  - offres de 4,99 à 97,99 $/mois sur 36 mois ;
  - renouvellement plus cher ;
  - licence cPanel à 15 $/mois (inutile ici) ;
  - à confirmer sur la page de paiement ;
  - à prévoir en plus : nom de domaine, service SMTP (souvent gratuit sous un certain volume), stockage externe des sauvegardes (quelques $/mois).
- **Compétence requise** : administrer un serveur Linux (mises à jour, sécurité). Si personne ne peut le faire, envisager un prestataire ou un hébergeur infogéré.
