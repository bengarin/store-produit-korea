# Meta Pixel — intégration, événements et tests

Pixel : `1665012938525216` (identifiant public). Code : `src/analytics/`.

## 1. Audit avant installation (2 novembre 2026)

Recherche dans tout le dépôt et tout l'historique Git : `fbq`, `fbevents`, `facebook`, `1665012938525216`,
Google Tag Manager (`GTM-`, `dataLayer`, `gtag`), Conversions API (`graph.facebook`), autres traceurs.
**Résultat : aucune intégration existante.** Aucun risque de double installation dans le code. Le module vérifie
quand même qu'un `fbq` n'existe pas déjà avant d'injecter le script (cas d'un ajout ultérieur via GTM).

## 2. Principes

| Règle | Mise en œuvre |
|-------|---------------|
| Consentement | **Aucun bandeau depuis le 05/11/2026** (décision de la propriétaire) : le pixel est chargé dès la première page de la boutique. Conformité (CNDP, visiteurs UE, conditions Meta) : à traiter par la personne responsable, voir docs/CONFIDENTIALITE.md. |
| Une seule instance | `fbevents.js` injecté une fois par chargement de page, `init` une seule fois (testé). |
| SPA React | Un `PageView` par entrée d'historique (`location.key`), pas au chargement du script. Changer de langue n'est pas une navigation. |
| StrictMode | Garde au niveau du module (effets appelés deux fois en développement) : testé sans doublon. |
| Périmètre | Boutique publique en **mode API** uniquement. Jamais dans l'administration, l'aperçu du thème, ni le mode démo (commandes simulées). |
| CSP | Aucun script en ligne. CSP : `script-src 'self' https://connect.facebook.net`, envois vers `https://www.facebook.com`. |
| `<noscript>` officiel | **Non installé** (visiteurs sans JavaScript non suivis). |
| Pas d'envoi automatique de Meta | `fbq.disablePushState = true` (sinon fbevents.js enverrait un PageView automatique à chaque changement d'URL de l'application, en double) et `fbq('set','autoConfig',false,ID)` (pas d'événements automatiques sur les clics). [À VÉRIFIER avec le vrai script dans Events Manager : non testable ici.] |

## 3. Événements

| Événement | Déclenchement | Paramètres |
|-----------|---------------|------------|
| PageView | chaque navigation réelle | — |
| ViewContent | ouverture d'une fiche produit | content_ids, content_type, content_name, contents, value, currency=MAD |
| AddToCart | ajout réel au panier (fiche, carte, rituel) | idem, value = prix réel × quantité |
| RemoveFromCart | retrait d'une ligne du panier | idem — **événement personnalisé** (`trackCustom`) : il n'existe pas en standard chez Meta |
| AddToWishlist | ajout aux favoris (pas au retrait) | idem |
| InitiateCheckout | ouverture de la page de commande avec des articles | content_ids, contents, num_items, value (total avec livraison), currency |
| AddPaymentInfo | envoi du formulaire **valide** avec le mode de paiement (à la livraison), une fois par tentative | idem + payment_method=cod |
| Purchase | **après** la réponse du serveur confirmant la création de la commande (numéro reçu) | idem, value = total calculé par le serveur, num_items, order_id ; eventID = `purchase.<numéro>` |
| Contact | clic sur un lien WhatsApp / `tel:` / `mailto:` | content_name = whatsapp / phone / email |
| Search | **non applicable** : la boutique n'a pas de recherche. Rien n'est inventé. | — |

Identifiants : `content_ids` = identifiant public du produit (slug, ex. `baroness-aloe-vera-gel`). Un futur
catalogue Meta doit utiliser les mêmes identifiants. Prix : ceux du catalogue (API), jamais des valeurs inventées.

**Paiement à la livraison** : Purchase = commande enregistrée (statut « en attente », pas encore payée). Aucun
Purchase si le formulaire est invalide, si le serveur refuse (stock, validation, anti-abus) ou en mode démo.
Rechargement, retour arrière ou nouvel onglet sur la confirmation : aucun Purchase (numéros déjà envoyés
mémorisés dans le navigateur + eventID stable pour la déduplication côté Meta).
[HYPOTHÈSE à valider] Optimiser les campagnes sur « commande enregistrée » surestime les ventes réelles
(refus à la livraison). Voir §5.

## 4. Tests (2 novembre 2026)

Meta Pixel Helper et Events Manager **non utilisables ici** : les domaines de Meta sont bloqués dans
l'environnement de test. Les tests interceptent `fbevents.js` et enregistrent chaque appel `fbq` ; **aucune
requête n'est envoyée à Meta** (vérifié : 0).

- `pixel_e2e` (build de production servi par Django, CSP réelle) : **33/33**. Consentement refusé/accepté,
  1 script et 1 init par page, PageView par navigation, ViewContent, AddToWishlist (pas au retrait),
  AddToCart 2 × 129 = 258 MAD, RemoveFromCart en trackCustom, InitiateCheckout 278 MAD, AddPaymentInfo,
  commande refusée (400) → aucun Purchase, commande créée → 1 Purchase (valeur serveur, eventID), 2 rechargements
  + retour/avance → 0 Purchase, Contact WhatsApp, 0 violation CSP, 0 erreur JavaScript.
- Mode développement (React StrictMode) : 1 ViewContent, 1 AddToCart, 1 InitiateCheckout — aucun doublon.

**Non vérifié** : réception réelle par Meta, déduplication côté Meta, Pixel Helper. → À faire sur une adresse
de test avant l'ouverture (§6).

## 5. Conversions API (serveur)

**N'existe pas.** Évaluation : utile (bloqueurs de publicité, iOS) et surtout pertinente pour le paiement à la
livraison : le serveur pourrait envoyer l'achat **à la livraison réelle** (vrai chiffre d'affaires) au lieu de la
simple commande. La déduplication est prévue : même `event_id` = `purchase.<numéro>`.
**Non activée** : aucun jeton n'a été fourni et aucun n'a été inventé. Avant activation, il faut :
1. un jeton d'accès Conversions API (Events Manager → Paramètres), stocké **uniquement** en variable
   d'environnement du serveur, jamais dans le front ni dans Git ;
2. décider de l'événement serveur (création de commande ou livraison) ;
3. décider si le téléphone (haché SHA-256) est transmis — cela demande une base légale et une mention dans la
   politique de confidentialité [À VÉRIFIER avec un juriste : loi 09-08, déclaration CNDP] ;
4. un code d'événement test pour valider dans Events Manager.

## 6. À faire dans Meta Events Manager (par le propriétaire)

1. Vérifier le domaine définitif (Business Settings → Brand Safety → Domains).
2. Sur l'adresse de test : Pixel Helper + onglet « Test Events » → parcourir le §4 et confirmer chaque événement.
3. Mesure agrégée (iOS) : classer les événements par priorité (Purchase en premier).
4. Si un catalogue est créé : identifiants produits = slugs de la boutique.
5. Ne pas ajouter le pixel une seconde fois via GTM ou un autre outil.
6. Paramètres du pixel → **désactiver la « correspondance avancée automatique »** (Automatic Advanced Matching) :
   la politique de confidentialité indique que nom, téléphone et adresse ne sont pas envoyés à Meta ; ce réglage
   de Meta pourrait sinon lire les champs du formulaire de commande. [À VÉRIFIER dans Events Manager]

## 7. Points à décider

- Politique de confidentialité : page `/confidentialite` (FR/AR), liée depuis le bandeau et le pied de page.
  Texte d'information **non validé juridiquement** (mention visible tant que `privacyPolicyReviewed` vaut false).
- Désactiver le pixel : `VITE_META_PIXEL_ID=off` au moment du build.

## 8. Dépannage : Meta Pixel Helper affiche « No Pixels found »

C'est **normal** dans 2 cas (aucun bug) ; en développement, la console du navigateur indique lequel :

| Message dans la console (`npm run dev`) | Cause | Solution |
|---|---|---|
| `[Meta Pixel] inactif : mode démo…` | `VITE_API_BASE_URL` vide : le site affiche les produits de démo et le pixel est volontairement coupé (commandes simulées) | Créer `.env.local` avec `VITE_API_BASE_URL=/api/v1/store`, lancer Django (`python manage.py runserver`), relancer `npm run dev` |
| `[Meta Pixel] inactif : VITE_META_PIXEL_ID…` | Identifiant absent, invalide ou `off` | Mettre `VITE_META_PIXEL_ID=1665012938525216` (ou supprimer la ligne : valeur par défaut) |

En mode API, les fiches **en brouillon** n'apparaissent pas : pour tester ViewContent / AddToCart / Purchase, au moins
un produit doit être **Actif** (prix > 0, stock renseigné). Test vérifié le 3 nov. 2026 sur `localhost:5173` (Vite dev,
mode API) : `fbevents.js` chargé 1 fois, `init 1665012938525216` 1 fois, PageView à chaque page, ViewContent,
AddToCart, InitiateCheckout, AddPaymentInfo, Purchase unique (`eventID purchase.<numéro>`), aucun Purchase au
rechargement ni en visite directe de `/confirmation`.
