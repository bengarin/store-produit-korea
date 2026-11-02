/**
 * Validation d'un thème (navigateur). Même règles que backend/apps/themes/validation.py, à partir du même
 * schéma partagé (shared/theme/schema.json) ; le serveur reste l'autorité. Aucun HTML, CSS ni script :
 * chaque valeur est un texte, une couleur #rrggbb, un choix dans une liste fermée, un lien contrôlé
 * ou une référence (image, produit, catégorie).
 * validateTheme(data) → { ok, value (normalisé), errors: [{ path, message }] }
 */
import SCHEMA from '../../shared/theme/schema.json';

export { SCHEMA };
const AREAS = { announcement: 'announcement_bar', header: 'header', footer: 'footer' };
const TOP_KEYS = ['schemaVersion', 'settings', 'announcement', 'header', 'home', 'footer'];
const ID_RE = new RegExp(SCHEMA.limits.idPattern);
const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,119}$/;
const HTML_RE = /[<>]/;
// eslint-disable-next-line no-control-regex
const CONTROL_RE = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/;
const LINK_RES = {
  internal: /^\/(?!\/)[A-Za-z0-9\-._~/?=&%+]*$/,
  anchor: /^#[a-z][a-z0-9-]{0,39}$/,
  external: /^https:\/\/[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+(\/[A-Za-z0-9\-._~/?=&%+#]*)?$/,
};

const isObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

/** Valide une valeur selon la définition d'un champ. Retourne [valeurNormalisée, messageErreur|null]. */
export function checkField(field, raw) {
  const value = raw === undefined || raw === null ? field.default : raw; // absent ou null = valeur par défaut
  switch (field.type) {
    case 'text':
    case 'textarea': {
      if (typeof value !== 'string') return [value, 'Texte attendu.'];
      const v = field.type === 'text' ? value.replace(/\s+/g, ' ').trim() : value.replace(/\r\n?/g, '\n').trim();
      if (HTML_RE.test(v)) return [v, 'Les caractères < et > (balises HTML) ne sont pas autorisés.'];
      if (CONTROL_RE.test(v)) return [v, 'Caractères invisibles non autorisés.'];
      if (field.maxLength && v.length > field.maxLength) return [v, `${field.maxLength} caractères maximum.`];
      if (field.required && !v) return [v, 'Champ obligatoire.'];
      return [v, null];
    }
    case 'color':
      if (typeof value !== 'string' || !/^#[0-9a-fA-F]{6}$/.test(value)) return [value, 'Couleur attendue au format #RRGGBB.'];
      return [value.toLowerCase(), null];
    case 'select':
      return field.options.some((o) => o.value === value) ? [value, null] : [value, 'Choix non autorisé.'];
    case 'font':
      return Object.hasOwn(SCHEMA.fonts, value) ? [value, null] : [value, 'Police non autorisée.'];
    case 'icon':
      return SCHEMA.icons.includes(value) ? [value, null] : [value, 'Icône non autorisée.'];
    case 'link': {
      if (typeof value !== 'string') return [value, 'Lien invalide.'];
      const v = value.trim();
      if (!v) return [v, field.required ? 'Champ obligatoire.' : null];
      const kinds = field.kinds || ['internal', 'anchor', 'external'];
      if (v.length > 300 || !kinds.some((k) => LINK_RES[k].test(v))) {
        return [v, kinds.length === 1 ? 'Lien interne attendu (ex. /produits).' : 'Lien interne (/produits), ancre (#collection) ou adresse https:// uniquement.'];
      }
      return [v, null];
    }
    case 'image': {
      if (value === null || value === undefined || value === '') return [null, field.required ? 'Image obligatoire.' : null];
      if (!isObject(value) || Object.keys(value).length !== 1) return [value, 'Image invalide.'];
      if ('asset' in value) return (field.assets || []).includes(value.asset) ? [{ asset: value.asset }, null] : [value, 'Image non autorisée.'];
      if (Number.isInteger(value.mediaId) && value.mediaId > 0) return [{ mediaId: value.mediaId }, null];
      return [value, 'Image invalide.'];
    }
    case 'product':
    case 'category': {
      if (typeof value !== 'string') return [value, 'Référence invalide.'];
      if (!value) return ['', field.required ? 'Champ obligatoire.' : null];
      return SLUG_RE.test(value) ? [value, null] : [value, 'Référence invalide.'];
    }
    default:
      return [value, 'Type de champ inconnu.'];
  }
}

function checkFields(fields, raw, path, errors) {
  const out = {};
  if (!isObject(raw)) {
    errors.push({ path, message: 'Objet attendu.' });
    return out;
  }
  const known = new Set(fields.map((f) => f.id));
  Object.keys(raw).filter((k) => !known.has(k)).forEach((k) => errors.push({ path: `${path}.${k}`, message: 'Réglage inconnu.' }));
  fields.forEach((f) => {
    const [v, err] = checkField(f, raw[f.id]);
    out[f.id] = v;
    if (err) errors.push({ path: `${path}.${f.id}`, message: err });
  });
  return out;
}

function checkSection(raw, path, errors, ids, expectedArea) {
  if (!isObject(raw)) {
    errors.push({ path, message: 'Section invalide.' });
    return null;
  }
  const def = SCHEMA.sections[raw.type];
  if (!def || def.area !== expectedArea) {
    errors.push({ path: `${path}.type`, message: 'Type de section non autorisé ici.' });
    return null;
  }
  const allowed = new Set(['id', 'type', 'disabled', 'settings', ...(def.items ? ['items'] : [])]);
  Object.keys(raw).filter((k) => !allowed.has(k)).forEach((k) => errors.push({ path: `${path}.${k}`, message: 'Clé inconnue.' }));
  if (typeof raw.id !== 'string' || !ID_RE.test(raw.id)) errors.push({ path: `${path}.id`, message: 'Identifiant invalide.' });
  else if (ids.has(raw.id)) errors.push({ path: `${path}.id`, message: 'Identifiant en double.' });
  else ids.add(raw.id);
  if (raw.disabled !== undefined && typeof raw.disabled !== 'boolean') errors.push({ path: `${path}.disabled`, message: 'Vrai ou faux attendu.' });
  const section = { id: raw.id, type: raw.type, disabled: Boolean(raw.disabled), settings: checkFields(def.settings, raw.settings ?? {}, `${path}.settings`, errors) };
  if (def.items) {
    const items = raw.items ?? [];
    if (!Array.isArray(items)) errors.push({ path: `${path}.items`, message: 'Liste attendue.' });
    else {
      if (items.length < def.items.min) errors.push({ path: `${path}.items`, message: `${def.items.min} élément(s) minimum.` });
      if (items.length > def.items.max) errors.push({ path: `${path}.items`, message: `${def.items.max} éléments maximum.` });
      section.items = items.slice(0, def.items.max).map((it, i) => checkFields(def.items.settings, it, `${path}.items.${i}`, errors));
    }
  }
  return section;
}

export function validateTheme(data) {
  const errors = [];
  if (!isObject(data)) return { ok: false, value: null, errors: [{ path: '', message: 'Thème invalide.' }] };
  Object.keys(data).filter((k) => !TOP_KEYS.includes(k)).forEach((k) => errors.push({ path: k, message: 'Clé inconnue.' }));
  if (data.schemaVersion !== SCHEMA.schemaVersion) errors.push({ path: 'schemaVersion', message: 'Version de schéma non prise en charge.' });
  const ids = new Set();
  const value = { schemaVersion: SCHEMA.schemaVersion, settings: checkFields(SCHEMA.settings, data.settings ?? {}, 'settings', errors) };
  Object.entries(AREAS).forEach(([area]) => {
    value[area] = checkSection(data[area], area, errors, ids, area);
  });
  const home = Array.isArray(data.home) ? data.home : null;
  if (!home) errors.push({ path: 'home', message: 'Liste de sections attendue.' });
  else {
    if (home.length > SCHEMA.limits.maxHomeSections) errors.push({ path: 'home', message: `${SCHEMA.limits.maxHomeSections} sections maximum.` });
    const counts = {};
    value.home = home.map((s, i) => {
      const section = checkSection(s, `home.${i}`, errors, ids, 'home');
      if (section) {
        counts[section.type] = (counts[section.type] || 0) + 1;
        const max = SCHEMA.sections[section.type].max;
        if (max && counts[section.type] > max) errors.push({ path: `home.${i}.type`, message: `${max} section(s) « ${SCHEMA.sections[section.type].name} » maximum.` });
      }
      return section;
    }).filter(Boolean);
  }
  return { ok: errors.length === 0, value, errors };
}

/** Nouvelle section avec les valeurs par défaut du schéma (ajout depuis l'éditeur). */
export function newSection(type, id) {
  const def = SCHEMA.sections[type];
  const settings = Object.fromEntries(def.settings.map((f) => [f.id, f.default ?? null]));
  const section = { id, type, disabled: false, settings };
  if (def.items) {
    const item = Object.fromEntries(def.items.settings.map((f) => [f.id, f.default ?? '']));
    section.items = Array.from({ length: def.items.min }, () => ({ ...item }));
  }
  return section;
}

export const newItem = (type) => Object.fromEntries(SCHEMA.sections[type].items.settings.map((f) => [f.id, f.default ?? '']));
