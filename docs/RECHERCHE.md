# Recherche produits

- **Où** : loupe dans l'en-tête (ordinateur : à droite ; mobile : à côté du menu ☰) et champ en haut de
  la page produits. Adresse partageable : `/produits?q=creme`.
- **Suggestions instantanées** : jusqu'à 5 produits (photo, nom, prix) pendant la saisie ; ↑ ↓ + Entrée pour
  ouvrir une fiche ; Entrée seule ou « Voir les N résultats » → page de résultats. Fermeture : Échap, ×, clic
  en dehors.
- **Ce qui est cherché** : nom, marque, accroche, types de peau, points forts, catégories et sous-catégories,
  résumé, ingrédients, bienfaits, utilisation, description — en français **et** en arabe, quelle que soit la
  langue du site. Majuscules, accents et voyelles arabes ignorés ; pluriel simple (« crèmes » = « crème »).
  Tous les mots doivent être trouvés ; le nom et la marque passent en premier.
- **Combinable** avec les filtres de catégorie de la page produits.
- **Mesure** : événement Meta Pixel standard `Search` (`search_string`) à chaque page de résultats, seulement si
  le pixel est actif et accepté.
- **Technique** : 100 % navigateur (le catalogue public est déjà chargé) — aucune modification du backend, de la
  base ou des migrations. Code : `src/utils/search.js`, `src/components/HeaderSearch.jsx`,
  `src/pages/ProductsPage.jsx`.
- **Limite** : pas de tolérance aux fautes de frappe (« creem » ne trouve rien). À revoir si le catalogue dépasse
  quelques centaines de produits (recherche côté serveur).
