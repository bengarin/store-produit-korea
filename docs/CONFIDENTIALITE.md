# Politique de confidentialité — état et éléments à fournir

Page : `/confidentialite` (français et arabe). Code : `src/pages/PrivacyPage.jsx`, texte : `src/i18n/privacy.js`.

**Statut : document d'information NON validé juridiquement.** La page l'indique tant que
`privacyPolicyReviewed` vaut `false` dans `src/config/store.js`. Elle n'est pas indexée par les moteurs de recherche
(`noindex`) pour l'instant. Ne passer `privacyPolicyReviewed` à `true` qu'après relecture par un professionnel du droit.

Le texte décrit uniquement ce que la boutique fait réellement : données de commande, newsletter facultative,
adresse IP et navigateur lors d'une commande (anti-fraude), stockage dans le navigateur (panier, favoris, langue,
choix cookies), pixel Meta seulement après « Accepter », aucune donnée bancaire (paiement à la livraison).
> Depuis le 05/11/2026, ce n'est plus exact pour le pixel Meta et le choix cookies : voir la section « À revoir » ci-dessous.

## Éléments affichés « à compléter » (rien n'a été inventé)

| Élément | Où le renseigner |
|---------|------------------|
| Raison sociale, adresse, e-mail et téléphone de contact | Admin → Paramètres (repris automatiquement par la page) |
| Société de livraison | Texte `src/i18n/privacy.js` (FR et AR) |
| Hébergeur et fournisseur d'e-mails | Texte `src/i18n/privacy.js` (FR et AR) |
| Durées de conservation (commandes, clients, newsletter) | Texte `src/i18n/privacy.js` — à fixer avec un juriste / comptable |

## ⚠️ À revoir par la personne responsable de la conformité (signalé le 05/11/2026)

Le bandeau de consentement aux cookies a été **retiré du code** à la demande de la propriétaire : le pixel Meta est
désormais chargé dès l'arrivée sur la boutique, sans « Accepter » ni « Refuser ». Le texte de la page
`/confidentialite` (`src/i18n/privacy.js`, FR et AR) **n'a pas été modifié** : les décisions juridiques reviennent à
la personne responsable. Phrases qui ne correspondent plus au fonctionnement réel :

| Section (FR / AR) | Phrase actuelle | Écart |
|---|---|---|
| Finalités | « Mesurer l'efficacité de nos publicités… **uniquement avec votre accord** » | Aucun accord n'est demandé |
| Cookies et pixel Meta | « Il n'est pas chargé et aucune donnée n'est envoyée à Meta **avant que vous cliquiez sur « Accepter »**. Si vous refusez, rien n'est chargé. » | Le pixel est chargé dès la première page |
| Cookies et pixel Meta | « **Après acceptation**, sont transmis à Meta : … » | Transmis sans acceptation |
| Cookies et pixel Meta | « Vous pouvez changer d'avis à tout moment avec **le bouton ci-dessous ou le lien « Cookies »** en bas de chaque page. » | Ce bouton et ce lien n'existent plus |
| Données stockées dans le navigateur | « … **votre choix concernant les cookies** … » | Plus aucun choix n'est enregistré |
| Données personnelles (section « Vos droits / cookies » en AR) | Équivalents arabes des phrases ci-dessus | Mêmes écarts |

Points de conformité à trancher par la personne responsable (non traités ici) : consentement préalable exigé par la
CNDP pour les cookies utilisant des données personnelles, visiteurs de l'Union européenne, conditions d'utilisation
des outils professionnels de Meta (l'annonceur est responsable du consentement). Le drapeau `consentButton` reste
dans `src/i18n/privacy.js` mais n'affiche plus rien.

## À vérifier avec un juriste [À VÉRIFIER]

- Obligations de déclaration ou d'autorisation auprès de la CNDP (loi 09-08) et mention éventuelle du numéro.
- Bases légales retenues, durées de conservation, transferts hors du Maroc (Meta, hébergeur).
- Mécanisme de consentement aux cookies (retiré du code le 05/11/2026).
