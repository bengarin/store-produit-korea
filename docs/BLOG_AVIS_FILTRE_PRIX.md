# Blog, avis clients et filtre prix

## Mise en place sur ton PC (une seule fois)
Deux nouvelles tables (articles du blog, avis sur la boutique). **Aucune table existante n'est modifiée.**

```bash
cd backend
python manage.py migrate blog
python manage.py migrate reviews
```
Faire une sauvegarde de la base avant (voir docs de sauvegarde). Rien d'autre à lancer.

## 1. Blog
- **Boutique** : lien « Blog » dans la navigation (et dans le menu ☰ mobile, et en bas de page).
  `/blog` = cartes (image, titre, résumé, date, « Lire la suite ») ; `/blog/<adresse>` = article.
- **Admin → Blog** : nouvel article, modifier, publier / dépublier, supprimer.
  - Français obligatoire ; arabe facultatif (vide = texte français affiché en arabe).
  - Couverture : choisie dans la médiathèque ou importée (convertie en WebP).
  - Brouillon = invisible. Publier sans date = maintenant ; date future = publication programmée.
  - Texte : gras, titres, listes, liens (rien d'autre, nettoyé par le serveur).
- **Droits** : lecture toute l'équipe · écrire/publier : Propriétaire, Admin, Éditeur · supprimer : Propriétaire, Admin.
- **Google** : titre, description, image de partage et données « BlogPosting » ; articles publiés dans le sitemap.

## 2. Filtre prix (page produits)
- Bouton « Prix » → prix minimum / maximum (DH) + curseur à deux poignées → « Appliquer ».
- « Effacer les filtres » : retire catégorie, recherche et prix.
- Se combine avec les catégories et la recherche. Adresse partageable : `/produits?prix_min=100&prix_max=250`.
- Le prix filtré = le prix affiché sur la carte produit.

## 3. Avis clients (sur la BOUTIQUE, pas sur un produit)
- **Boutique** : page `/avis` (lien en bas de page et dans le menu ☰ mobile) : note moyenne, avis publiés
  (prénom, étoiles, texte, date) et formulaire (note, prénom, avis, case d'accord de publication).
- **Rien n'est publié sans validation.** Admin → Avis clients (pastille = avis en attente) :
  approuver, modifier (fautes, contenu inapproprié), dépublier, supprimer.
- Protection : 5 envois max par heure et par connexion, champ piège anti-robots, liens et HTML refusés.
  Aucune adresse e-mail ni téléphone demandés.
- Les « Témoignages » de la page d'accueil (thème) restent séparés et inchangés.
- **Droits** : modération : Propriétaire, Admin, Éditeur · suppression : Propriétaire, Admin.

## À vérifier
- [À VÉRIFIER] Textes arabes de l'interface (blog, avis, filtre) par une personne arabophone.
- [À VÉRIFIER juridique] Publication du prénom avec accord explicite (loi 09-08) : texte de la case à faire valider.
- Mode démo (sans serveur) : blog vide et formulaire d'avis désactivé (rien n'est inventé).
