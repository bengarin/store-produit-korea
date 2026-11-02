# Politique de confidentialité — état et éléments à fournir

Page : `/confidentialite` (français et arabe). Code : `src/pages/PrivacyPage.jsx`, texte : `src/i18n/privacy.js`.

**Statut : document d'information NON validé juridiquement.** La page l'indique tant que
`privacyPolicyReviewed` vaut `false` dans `src/config/store.js`. Elle n'est pas indexée par les moteurs de recherche
(`noindex`) pour l'instant. Ne passer `privacyPolicyReviewed` à `true` qu'après relecture par un professionnel du droit.

Le texte décrit uniquement ce que la boutique fait réellement : données de commande, newsletter facultative,
adresse IP et navigateur lors d'une commande (anti-fraude), stockage dans le navigateur (panier, favoris, langue,
choix cookies), pixel Meta seulement après « Accepter », aucune donnée bancaire (paiement à la livraison).

## Éléments affichés « à compléter » (rien n'a été inventé)

| Élément | Où le renseigner |
|---------|------------------|
| Raison sociale, adresse, e-mail et téléphone de contact | Admin → Paramètres (repris automatiquement par la page) |
| Société de livraison | Texte `src/i18n/privacy.js` (FR et AR) |
| Hébergeur et fournisseur d'e-mails | Texte `src/i18n/privacy.js` (FR et AR) |
| Durées de conservation (commandes, clients, newsletter) | Texte `src/i18n/privacy.js` — à fixer avec un juriste / comptable |

## À vérifier avec un juriste [À VÉRIFIER]

- Obligations de déclaration ou d'autorisation auprès de la CNDP (loi 09-08) et mention éventuelle du numéro.
- Bases légales retenues, durées de conservation, transferts hors du Maroc (Meta, hébergeur).
- Texte du bandeau de consentement.
