# Référencement (SEO) et moteurs de réponse IA (GEO)

## Contenu visible sans JavaScript (audit G2)
Le serveur Django écrit le contenu principal de chaque page dans `<div id="root">` (`backend/apps/seo/content.py`) :
titres, produits (nom, prix, disponibilité, lien), fiche produit complète (description, bienfaits, ingrédients,
utilisation), catégories, articles du blog, avis publiés, menu de liens. Les robots qui n'exécutent pas JavaScript
(moteurs de réponse IA, aperçus de liens) lisent donc la vraie page. L'application React remplace ce contenu au
démarrage (même information, mise en page complète ; aucun décalage visuel mesuré).

## Premier affichage plus rapide (audit P1)
Les données de démarrage (produits, catégories, filtres, configuration, thème publiés) sont jointes à la page
(`<script id="mpc-data" type="application/json">`, `backend/apps/seo/bootstrap.py`) : l'application ne fait plus
5 appels réseau avant d'afficher. Sans ces données (serveur de développement Vite), elle appelle les API comme avant.
Mesure (mobile simulé 4G lente, processeur ralenti ×4) : premier affichage 3,4–3,7 s → 1,3 s.

## Pages arabes indexables (audit G1)
- Français : adresses historiques inchangées (`/`, `/produits`, `/produits/<slug>`, `/blog`, `/avis`…).
- Arabe : mêmes pages sous `/ar` (`/ar`, `/ar/produits`, `/ar/produits/<slug>`, `/ar/blog`, `/ar/avis`…),
  servies avec `<html lang="ar" dir="rtl">`, titres et descriptions arabes, `og:locale` `ar_MA`.
- Chaque page publique : URL canonique dans sa langue + `hreflang` `fr-MA`, `ar-MA`, `x-default` (français).
- `sitemap.xml` : chaque page dans les deux langues, avec les liens entre versions ; `robots.txt` : `/ar/panier`,
  `/ar/commande`, `/ar/confirmation` exclus.
- Boutique : la langue vient de l'adresse ; le bouton de langue ouvre la même page dans l'autre langue ; un visiteur
  qui avait choisi l'arabe est envoyé sur l'adresse `/ar/…` correspondante. L'administration reste `/admin`.
- [À VÉRIFIER] Titres et descriptions arabes du serveur (`PAGE_TEXTS` dans `apps/seo/views.py`, `TEXTS` dans
  `apps/seo/content.py`) par une personne arabophone.

## Mise en ligne
Après `git pull` : `npm run build` (nouveau `dist/`), redémarrer gunicorn. Aucune migration.
Puis, dans Google Search Console : soumettre `/sitemap.xml` et vérifier quelques pages `/ar/…` (outil d'inspection).
