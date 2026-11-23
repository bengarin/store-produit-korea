# Import Shopify → Jodhur : mode d'emploi (copie de la base d'abord)

Une seule commande : `import_shopify`. Sans `--appliquer`, elle n'écrit RIEN (aperçu).
Détail champ par champ : `CORRESPONDANCE_CHAMPS.md`.

## 1. Préparer une copie de la base (PowerShell, dans `C:\workspace\store-produit-korea`)

```
git pull
mysqldump -u UTILISATEUR -p --result-file=sauvegarde_avant_import.sql NOM_DE_TA_BASE
mysql -u UTILISATEUR -p -e "CREATE DATABASE jodhur_essai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
cmd /c "mysql -u UTILISATEUR -p jodhur_essai < sauvegarde_avant_import.sql"
cd backend
$env:DB_NAME="jodhur_essai"
python manage.py shell -c "from django.db import connection; print(connection.settings_dict['NAME'])"
```
La dernière ligne doit afficher `jodhur_essai`. Sinon : STOP.

## 2. Sur la copie : migration, aperçu, application, relance

```
python manage.py migrate
python manage.py import_shopify --rendre-visibles utiles --report apercu.md --csv apercu.csv
python manage.py import_shopify --rendre-visibles utiles --appliquer --report rapport.md --csv rapport.csv
python manage.py import_shopify --rendre-visibles utiles --report relance.md
```
- `migrate` ajoute la migration `catalog 0012` (ajout de champs et d'une table, rien n'est supprimé).
- `apercu.md` : statut final, produits bloqués (champ manquant), catégories rendues visibles, valeurs Shopify sans
  correspondance, images à télécharger, modifications Jodhur conservées, détail produit par produit.
- `relance.md` doit indiquer « déjà à jour » partout (aucun doublon).
- Les images sont téléchargées dans `backend/media/` (dossier partagé avec la vraie base : sans effet sur elle).

Vérifier la boutique de la copie : `cd ..` → `npm run build` → `cd backend` → `python manage.py runserver`.

## 3. Revenir à la vraie base

```
Remove-Item Env:DB_NAME
python manage.py shell -c "from django.db import connection; print(connection.settings_dict['NAME'])"
```

La vraie base ne sera traitée qu'après validation de l'aperçu (même commandes, sans `$env:DB_NAME`).

## Lire directement Shopify (facultatif)

Par défaut, la commande lit l'export versionné `export_shopify_complet.json`. Pour lire Shopify en direct
(lecture seule) : créer une application personnalisée Shopify avec le droit `read_products`, puis

```
$env:SHOPIFY_STORE_DOMAIN="ma-boutique.myshopify.com"
$env:SHOPIFY_ADMIN_TOKEN="(jeton, à ne jamais partager)"
python manage.py import_shopify --source shopify --export export_du_jour.json --rendre-visibles utiles --report apercu.md
```
