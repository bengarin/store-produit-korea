# Filtres de la page produits

## Mise en place sur ton PC (une seule fois, après une sauvegarde)
Nouvelle table de filtres, **aucune donnée produit modifiée** :
```bash
cd backend
python manage.py migrate catalog
```

## Boutique
- **Ordinateur** : colonne « Filtres » à gauche des produits (à droite en arabe) : Catégories, Prix (min / max en DH
  + curseur + « Appliquer »), puis les groupes créés dans l'admin, repliables. Chaque choix s'applique tout de suite.
- **Mobile** : bouton « Filtre » au-dessus des produits → tiroir avec ×, « Réinitialiser » et
  « Appliquer · N produits » (rien ne change tant qu'on n'a pas appuyé sur « Appliquer »).
- Barre au-dessus des produits : nombre de produits, **Trier par** (Recommandés = ordre de l'admin, Prix croissant,
  Prix décroissant, Nouveautés = date de première mise en ligne), puces des filtres actifs (× pour retirer) et
  « Effacer les filtres ».
- Règle : dans un même groupe, une valeur OU une autre ; entre groupes, ET. Le chiffre à côté de chaque valeur =
  produits disponibles avec les autres filtres déjà choisis.
- La recherche reste uniquement dans la loupe de l'en-tête ; ses résultats se filtrent et se trient comme le reste.
- Adresse partageable : `/produits?filtres=mes-solutions:hydratation&prix_min=100&prix_max=250&tri=prix-asc`.
- **Meilleures ventes** : [NON DISPONIBLE] la boutique ne publie pas de classement des ventes. Possible plus tard
  (calcul côté serveur à partir des commandes, sans jamais publier les chiffres).

## Admin → Filtres (Propriétaire, Admin)
- Créer un groupe (« Mes Solutions », « Zone d'application », « Type de peau »…) et ses valeurs, en FR et AR.
- Renommer, monter / descendre, masquer / afficher, supprimer (les produits restent intacts).
- Un groupe sans valeur visible n'apparaît pas dans la boutique.

## Fiche produit → carte « Filtres de la boutique » (Propriétaire, Admin, Éditeur)
- Cocher les valeurs du produit puis « Enregistrer les filtres ». Seuls ces liens changent (prix, stock, statut,
  catégories intacts).

## À vérifier
- [À VÉRIFIER] Les captures « Jodhur » n'ont pas été reçues : mise en page faite d'après la description écrite.
- [À VÉRIFIER] Textes arabes de l'interface (filtres, tri) par une personne arabophone.
