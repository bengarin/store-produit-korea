# Menu « Catégories »

Le lien « Nos produits » de la barre de navigation devient « Catégories » dès qu'au moins une catégorie est
visible. Tout le contenu du menu vient de la base de données, géré dans **Admin → Catégories**.

## Boutique

- **Ordinateur** : survol ou clic sur « Catégories » → panneau crème pleine largeur sous la barre, une colonne
  par catégorie (titre vert foncé en serif), sous-catégories en dessous. Voile gris-vert léger sur la page.
  Fermeture : après un choix, clic en dehors, touche Échap, ou en quittant le menu à la souris.
- **Mobile** : menu ☰ → « Catégories » (accordéon). Toucher un nom = ses produits ; toucher la flèche = ses
  sous-catégories.
- **Arabe** : libellés arabes saisis dans l'admin (vides = nom français), disposition de droite à gauche.
- **Filtrage** : une catégorie affiche ses produits **et** ceux de ses sous-catégories ; une sous-catégorie
  affiche les siens. Sur la page produits, une 2e ligne de filtres propose les sous-catégories.

## Admin → Catégories (rôles Propriétaire et Admin)

- Créer une catégorie ou une sous-catégorie (nom FR, nom AR, catégorie parente).
- Renommer, changer de parente, monter / descendre (ordre du menu), masquer / afficher, supprimer.
- « Produits » : cocher les produits existants de la catégorie. Seuls les liens de cette catégorie changent
  (jamais les prix, stocks, statuts ni les autres catégories). Un produit en ligne garde au moins une catégorie.
- Masquer une catégorie la retire du menu **avec ses sous-catégories** ; ses produits restent dans
  l'administration et en ligne.
- 2 niveaux seulement (catégorie → sous-catégories). Une catégorie qui a des sous-catégories ne peut être ni
  rangée sous une autre, ni supprimée.
- Les autres rôles voient les catégories (formulaire produit) mais ne peuvent pas les modifier.

Aucune migration : le modèle `Category` avait déjà `parent`, `position`, `is_active` et `name_ar`.

## Sous-catégories d'exemple (facultatif)

Libellés de la maquette, à ajouter puis modifier dans l'admin :

```bash
cd backend
python manage.py seed_menu_categories --dry-run   # aperçu, rien n'est écrit
python manage.py seed_menu_categories             # ajoute les manquantes (idempotent)
```

Hydratation → Gels apaisants, Crèmes hydratantes · Éclat → Crèmes anti-taches, Soins du teint ·
Anti-âge → Contour des yeux, Patchs yeux. Aucun produit n'y est rattaché d'office : à faire dans
Admin → Catégories → « Produits ». Les noms arabes proposés sont [À VÉRIFIER] par une personne arabophone.
