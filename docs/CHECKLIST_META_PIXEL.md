# Checklist — vérifier le pixel Meta dans Events Manager

Pixel : `1665012938525216`. À faire **sur une adresse de test non publique** (pas en local : Meta doit pouvoir
recevoir les événements), après votre accord pour l'installation de test. Rien n'a pu être vérifié côté Meta
depuis l'environnement de développement (domaines de Meta bloqués) : cette checklist sert justement à le faire.

## 0. Préparation

- [ ] Extension **Meta Pixel Helper** installée dans Chrome.
- [ ] Events Manager → Sources de données → pixel `1665012938525216` → onglet **« Tester les événements »**
      (Test Events) → saisir l'adresse de test → « Ouvrir le site ».
- [ ] Navigateur en navigation privée (aucun ancien choix de cookies).
- [ ] Produit de test disponible (stock > 0) — **ne pas modifier le stock des produits réels pour le test**.
- [ ] Prévenir l'équipe : la commande de test sera **annulée** ensuite dans l'admin (nom « Test Pixel »).

## 1. Chargement du pixel (aucun bandeau de consentement depuis le 05/11/2026)

- [ ] À l'arrivée sur la boutique : Pixel Helper détecte le pixel `1665012938525216`, **une seule fois**
      (pas d'avertissement « Duplicate Pixel ID » / « pixel chargé plusieurs fois »).

## 2. Événements à vérifier

| # | Action | Attendu dans Test Events | Paramètres à contrôler |
|---|--------|--------------------------|------------------------|
| 1 | Ouvrir l'accueil | **1 PageView** | — |
| 2 | Cliquer « منتجاتنا / Nos produits », puis une catégorie | **1 PageView par clic** (pas 2) | — |
| 3 | Ouvrir une fiche produit | 1 PageView + **1 ViewContent** | content_ids = identifiant du produit (ex. `baroness-aloe-vera-gel`), value = prix, currency = **MAD** |
| 4 | Changer la langue (FR ↔ AR) | **Aucun** nouvel événement | — |
| 5 | Ajouter 2 unités au panier | **1 AddToCart** | contents.quantity = 2, value = 2 × prix, currency = MAD |
| 6 | Ajouter aux favoris (♡) | 1 AddToWishlist (rien au retrait) | value = prix |
| 7 | Retirer un article du panier | 1 **RemoveFromCart** (événement **personnalisé**) | — |
| 8 | « Passer la commande » | **1 InitiateCheckout** | num_items, value = total avec livraison, currency = MAD |
| 9 | Envoyer le formulaire valide | 1 AddPaymentInfo | payment_method = cod |
| 10 | Commande créée (page de confirmation) | **1 Purchase** | value = total de la commande, currency = MAD, order_id = numéro affiché ; ID d'événement = `purchase.<numéro>` |
| 11 | Recharger la confirmation 2 fois, retour arrière | **Aucun** Purchase supplémentaire | — |
| 12 | Clic WhatsApp (si le numéro est configuré) | 1 Contact | content_name = whatsapp |

Points d'attention :
- [ ] **PageView jamais en double** sur une même navigation. Un doublon signifierait que l'envoi automatique de Meta
      sur changement d'URL n'est pas désactivé (le code met `fbq.disablePushState = true`) → me le signaler.
- [ ] Aucun événement **non listé** ci-dessus (ex. « SubscribedButtonClick », « Microdata ») : sinon les événements
      automatiques de Meta sont actifs → voir §3.
- [ ] Commande refusée (ex. formulaire incomplet) : **pas** de Purchase.
- [ ] Après le test : **annuler la commande de test** dans l'admin. [À VÉRIFIER] Les événements reçus via
      « Tester les événements » peuvent être comptés dans les statistiques : noter la date et l'heure du test.

## 3. Correspondance avancée automatique (Automatic Advanced Matching) — à DÉSACTIVER

La politique de confidentialité indique que **ni le nom, ni le téléphone, ni l'adresse** ne sont envoyés à Meta.
Ce réglage de Meta peut lire les champs du formulaire de commande : il doit être désactivé pour que ce soit vrai.

- [ ] Events Manager → pixel → **Paramètres** → « Correspondance avancée automatique » → **désactivée**.
      [À VÉRIFIER] l'intitulé exact peut varier selon l'interface de Meta.
- [ ] Même page : « Suivre les événements automatiquement sans code » (événements automatiques) → **désactivé**.
- [ ] Contrôle : dans Test Events, ouvrir le détail du Purchase → **aucun** paramètre de correspondance
      (em, ph, fn, ln, ct…) ne doit apparaître.

## 4. Réglages du compte Meta (une fois)

- [ ] Vérifier le **domaine** définitif (Paramètres de l'entreprise → Sécurité de la marque → Domaines).
- [ ] Mesure agrégée des événements (iOS) : **Purchase** en priorité 1.
- [ ] Ne pas installer le pixel une seconde fois (GTM, plugin, autre outil).
- [ ] Conversions API : **non activée**. Ne jamais coller de jeton d'accès dans le site ; il se configure côté serveur
      (voir `docs/META_PIXEL.md` §5).

## 5. Résultat à me transmettre

Pour chaque ligne du §2 : ✅ / ❌ + capture d'écran du détail en cas d'écart. Avec ces retours, je corrige
avant toute ouverture publique.
