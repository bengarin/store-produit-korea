# Shopify → Jodhur : où va chaque champ

Commande unique : `python manage.py import_shopify --rendre-visibles utiles` (aperçu) puis la même avec `--appliquer` (voir `MODE_EMPLOI_IMPORT.md`).
Données lues en lecture seule (export `export_shopify_complet.json` ou `--source shopify`). Shopify n'est jamais modifié.

« Mise à jour » = règle appliquée aux produits déjà présents : la valeur Jodhur n'est remplacée que si elle est
vide ou identique à la dernière valeur importée (sinon : modification manuelle → gardée et signalée).

## Produit

| Champ Shopify | Stockage Jodhur | Visible / utilisé | Mise à jour |
|---|---|---|---|
| `id` | `Product.shopify_id` | Admin (carte « Données Shopify ») ; clé anti-doublon | — |
| `handle` | `Product.slug` (création) + `Product.shopify_handle` | URL de la fiche ; admin | slug jamais changé (liens) ; handle recopié |
| `title` | `name`, `display_name` | Boutique (titre, cartes) ; admin | règle de mise à jour |
| `descriptionHtml` | `description_html` (HTML assaini) ; 1er paragraphe → `summary` | Boutique (rubrique Description, résumé) | règle de mise à jour |
| `vendor` | `brand` **et** `supplier` | Marque : boutique ; Fournisseur : admin seulement | règle de mise à jour |
| `productType` | `shopify_product_type` | Admin (lecture seule), recherche admin | recopié à chaque import |
| `category.fullName` | `shopify_category` + catégories Jodhur via le tableau de correspondances | Admin ; menu / filtres de la boutique (catégories Jodhur) | catégories : ajout seulement |
| `collections` | `shopify_collections` + catégories Jodhur (tableau) + collections Jodhur (nom identique) | Admin ; boutique (catégories / collections Jodhur) | ajout seulement |
| `tags` | `shopify_tags` | Admin (lecture seule) ; recherche admin | recopié à chaque import |
| `seo.title` | `seo_title` (70 car. max) | Balise `<title>` de la fiche | règle de mise à jour |
| `seo.description` | `seo_description` (160 car. max ; coupée au dernier mot entier si plus longue — signalé) | Méta-description | règle de mise à jour |
| `updatedAt` | `shopify_updated_at` | Admin | recopié |
| `status` (ACTIVE) | `status` = actif si les conditions d'activation sont remplies | Boutique | brouillon gardé si mis à la main ; archivé gardé |

## Variantes

| Champ Shopify | Stockage Jodhur | Visible / utilisé | Mise à jour |
|---|---|---|---|
| `id` | `Variant.shopify_id` | Clé anti-doublon | — |
| `title`, `selectedOptions`, `options` | `Variant.title`, options et valeurs (« size » → « Taille ») | Boutique (choix de la variante) | options créées à la création seulement |
| `sku` | `Variant.sku` (si non utilisé ailleurs) | Admin, commandes | règle de mise à jour |
| `barcodes` | `Variant.barcode` (si non utilisé ailleurs) | Admin, recherche admin | règle de mise à jour |
| `price` | `Variant.price` | Boutique | règle de mise à jour |
| `compareAtPrice` | `Variant.compare_at_price` (seulement s'il est supérieur au prix) | Prix barré | règle de mise à jour |
| `inventoryQuantity` | `Variant.stock_quantity` + mouvement de stock tracé | Disponibilité | règle de mise à jour (une vente Jodhur change le stock → gardé) |
| `inventoryItem.tracked` | `Variant.track_inventory` | Gestion du stock | règle de mise à jour |
| `inventoryPolicy` (CONTINUE) | `Variant.allow_backorder` | Vente sans stock | règle de mise à jour |
| `inventoryItem.measurement.weight` | `Variant.weight_grams` (si > 0) | Admin | règle de mise à jour |
| `media` de la variante | `Variant.image` | Boutique | si vide |

## Images

| Champ Shopify | Stockage Jodhur | Visible / utilisé |
|---|---|---|
| `media` (MediaImage) | Fichier téléchargé, ré-encodé WebP dans `MEDIA_ROOT/uploads/…` (`MediaAsset`), lié par `ProductImage` | Galerie de la fiche, servie par Jodhur (jamais l'URL Shopify) |
| ordre des médias | `ProductImage.position` | Ordre de la galerie (création ; images ajoutées ensuite à la fin) |
| `alt` | `ProductImage.alt` (vide → nom du produit, signalé) | Texte alternatif |
| `id` | `ProductImage.shopify_media_id` | Anti-doublon ; même fichier = relié, pas recopié (empreinte SHA-256) |

## Metafields (4 292 dans l'export : 63 clés différentes)

Tous sont stockés tels quels dans `ProductMetafield` (identifiant, espace de noms, clé, type, valeur brute) et affichés
dans l'admin (fiche produit → « Données Shopify » → « Metafields »). Jamais supprimés : un metafield disparu de
Shopify est marqué « absent de Shopify ».

Certains alimentent aussi un champ Jodhur (format converti, contenu inchangé) :

| Metafield | Champ Jodhur | Visible |
|---|---|---|
| `custom.ingredients` (texte riche) | `ingredients` (liste) | Boutique : rubrique Ingrédients |
| `custom.les_benefices` (texte riche) | `benefits` (liste, puces retirées) | Boutique : rubrique Bienfaits |
| `custom.utilisation` (texte riche) | `usage_steps` (liste) | Boutique : rubrique Utilisation |
| `custom.description_courte` | `short_description` seulement si ≤ 160 caractères (sinon signalé) | Cartes produits |
| `custom.type_de_peau` | `skin_types` | Boutique |

Stockés et visibles dans l'admin uniquement (aucun champ Jodhur équivalent aujourd'hui) :
`custom.faq_q*` / `faq_r*` (pas de section FAQ dans Jodhur), `custom.besoin_principal`, `custom.preoccupation`,
`custom.zone_d_application`, `custom.type_de_peau2` (utilisables plus tard pour les filtres),
`reviews.*` / `loox.*` (notes d'avis Shopify : non affichées, Jodhur a ses propres avis),
`global.title_tag` / `global.description_tag` (doublons du SEO), `mm-google-shopping.*`, `mc-facebook.*`,
`shopify.*` (attributs de la catégorie Shopify) et les références (`metaobject_reference`, `file_reference`) :
stockées telles quelles, **non résolues** (il faudrait lire les metaobjets / fichiers Shopify).
