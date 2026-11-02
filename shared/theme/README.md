# Thème de la boutique — fichiers partagés (front + backend)

| Fichier | Rôle |
|---|---|
| `schema.json` | **Registre** : réglages globaux, sections autorisées, champs, limites, polices, icônes, images intégrées |
| `default-theme.json` | Thème d'origine = l'accueil d'avant le thème (mode démo, aucun thème publié, API indisponible) |
| `test-cases.json` | Cas de validation partagés : Python (`backend/tests/test_themes.py`) et JavaScript (`node scripts/check-theme-validators.mjs`) doivent rendre le même verdict |

Lu par : `src/theme/validate.js` (navigateur) et `backend/apps/themes/validation.py` (serveur, autorité).
En production, ce dossier doit être déployé avec le backend (`THEME_SHARED_DIR` sinon `../shared/theme`).

## Format d'un thème

```json
{
  "schemaVersion": 1,
  "settings": { "colorPrimary": "#214a3b", "headingFont": "cormorant", "radius": "normal", "...": "..." },
  "announcement": { "id": "announcement", "type": "announcement_bar", "disabled": true, "settings": { "text": "…" } },
  "header": { "id": "header", "type": "header", "disabled": false, "settings": {}, "items": [{ "label": "Accueil", "link": "/" }] },
  "home": [ { "id": "hero", "type": "hero", "disabled": false, "settings": { "heading": "…", "imageDesktop": { "asset": "hero-wide" } } } ],
  "footer": { "id": "footer", "type": "footer", "disabled": false, "settings": { "text": "" }, "items": [] }
}
```

Types de champs (liste fermée) : `text`, `textarea` (texte brut, sans `<` ni `>`), `color` (`#rrggbb`), `select`, `font`,
`icon`, `link` (interne `/…`, ancre `#…` ou `https://…` ; jamais `javascript:`, `data:`, `http:`, `//`), `image`
(`{ "asset": clé autorisée }` ou `{ "mediaId": n }` existant en médiathèque), `product`, `category` (références vérifiées en base).
Toute clé inconnue est refusée. Taille max. 256 Ko, 20 sections d'accueil.

## Ajouter une section (ex. « FAQ »)

1. `schema.json` → `sections.faq` : `name`, `area: "home"`, `max`, `description`, `settings` (et `items` si liste).
2. `src/components/Faq.jsx` : composant de la boutique qui reçoit `{ section }` (textes affichés tels quels).
3. `src/theme/SectionRenderer.jsx` → `SECTION_COMPONENTS.faq = Faq`.
4. Ajouter des cas dans `test-cases.json` ; lancer `pytest` et `node scripts/check-theme-validators.mjs`.

Aucun formulaire à écrire : l'éditeur génère les champs à partir du schéma.
