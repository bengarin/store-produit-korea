/**
 * Réglages globaux du thème → variables CSS de global.css (aucune CSS libre : chaque valeur vient d'une
 * couleur #rrggbb validée ou d'une liste fermée). Seules les valeurs différentes du défaut sont posées.
 */
import { SCHEMA } from './validate.js';

const DEFAULTS = Object.fromEntries(SCHEMA.settings.map((f) => [f.id, f.default]));

/** Mélange une couleur #rrggbb avec une autre (ratio 0 → 1). */
export function mix(hex, other, ratio) {
  const a = hex.match(/\w\w/g).map((h) => parseInt(h, 16));
  const b = other.match(/\w\w/g).map((h) => parseInt(h, 16));
  return `#${a.map((v, i) => Math.round(v + (b[i] - v) * ratio).toString(16).padStart(2, '0')).join('')}`;
}

const RADIUS = { square: ['2px', '3px', '4px'], small: ['5px', '8px', '10px'], large: ['12px', '18px', '24px'] };
const BUTTON_RADIUS = { square: '2px', pill: '999px' };
const HEADING = { s: '0.88', l: '1.12', xl: '1.24' };
const SPACE = { compact: '0.7', spacious: '1.3' };

export function themeCssVars(settings = {}) {
  const s = { ...DEFAULTS, ...settings };
  const changed = (key) => s[key] !== DEFAULTS[key];
  const vars = {};
  if (changed('colorPrimary')) Object.assign(vars, { '--green': s.colorPrimary, '--green-hover': mix(s.colorPrimary, '#000000', 0.12) });
  if (changed('colorPrimaryDark')) vars['--green-deep'] = s.colorPrimaryDark;
  if (changed('colorAccent')) Object.assign(vars, { '--sage': s.colorAccent, '--sage-soft': mix(s.colorAccent, '#ffffff', 0.75) });
  if (changed('colorBackground')) vars['--bg'] = s.colorBackground;
  if (changed('colorSurface')) vars['--surface'] = s.colorSurface;
  if (changed('colorBeige')) Object.assign(vars, { '--beige': s.colorBeige, '--beige-hover': mix(s.colorBeige, '#000000', 0.05) });
  if (changed('colorText')) vars['--text'] = s.colorText;
  if (changed('colorTextSoft')) vars['--text-2'] = s.colorTextSoft;
  if (changed('buttonBackground')) Object.assign(vars, { '--btn-bg': s.buttonBackground, '--btn-bg-hover': mix(s.buttonBackground, '#000000', 0.12) });
  if (changed('buttonText')) vars['--btn-text'] = s.buttonText;
  if (BUTTON_RADIUS[s.buttonShape]) vars['--btn-radius'] = BUTTON_RADIUS[s.buttonShape];
  if (changed('headingFont') && SCHEMA.fonts[s.headingFont]) vars['--font-serif'] = SCHEMA.fonts[s.headingFont].stack;
  if (changed('bodyFont') && SCHEMA.fonts[s.bodyFont]) vars['--font-sans'] = SCHEMA.fonts[s.bodyFont].stack;
  if (HEADING[s.headingScale]) vars['--heading-scale'] = HEADING[s.headingScale];
  if (changed('contentWidth')) vars['--max-w'] = `${Number(s.contentWidth)}px`;
  if (SPACE[s.sectionSpacing]) vars['--space-scale'] = SPACE[s.sectionSpacing];
  if (RADIUS[s.radius]) [vars['--r-sm'], vars['--r'], vars['--r-lg']] = RADIUS[s.radius];
  return vars;
}

/** Polices hors de celles déjà chargées par index.html : feuille Google Fonts (familles de la liste fermée). */
export function fontStylesheets(settings = {}) {
  return [...new Set([settings.headingFont, settings.bodyFont])]
    .map((key) => SCHEMA.fonts[key]?.google)
    .filter(Boolean)
    .map((family) => `https://fonts.googleapis.com/css2?family=${family}&display=swap`);
}
