import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { ADMIN_API_BASE_URL, DATA_SOURCE } from '../config/env.js';
import { api } from '../api/client.js';
import { ENDPOINTS } from '../api/endpoints.js';
import DEFAULT_THEME from './defaultTheme.js';
import { validateTheme } from './validate.js';
import { fontStylesheets, themeCssVars } from './cssVars.js';

const ThemeContext = createContext({ theme: DEFAULT_THEME, media: {}, preview: false, status: 'ready' });

/**
 * Mode aperçu (éditeur de thème) : URL « ?apercu-theme=1 » à l'ouverture, dans une iframe ou un onglet de l'équipe.
 * Le brouillon n'est lu qu'avec une session de l'administration ; les visiteurs ne voient que le thème publié.
 */
export const PREVIEW = typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('apercu-theme');
export const PREVIEW_MESSAGE = 'mpc-theme-preview';

/** Thème vérifié (mêmes règles que le serveur) ; thème par défaut si invalide. */
function safeTheme(data) {
  if (!data) return DEFAULT_THEME;
  const { ok, value, errors } = validateTheme(data);
  if (ok) return value;
  console.warn('Thème invalide, thème par défaut utilisé.', errors.slice(0, 5));
  return DEFAULT_THEME;
}

async function loadDraft() {
  const res = await fetch(`${ADMIN_API_BASE_URL}/theme`, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(String(res.status));
  const data = await res.json();
  return { theme: data.draft.data, media: data.media || {}, version: 'draft' };
}

async function loadPublished() {
  const data = await api.get(ENDPOINTS.theme);
  return { theme: data.theme, media: data.media || {}, version: data.version };
}

export function ThemeProvider({ children }) {
  const isLocal = DATA_SOURCE === 'local';
  const [state, setState] = useState(() => ({
    status: isLocal && !PREVIEW ? 'ready' : 'loading', theme: DEFAULT_THEME, media: {}, version: null,
  }));

  useEffect(() => {
    if (isLocal && !PREVIEW) return undefined;
    let alive = true;
    const attempt = PREVIEW && ADMIN_API_BASE_URL
      ? loadDraft().catch(() => (isLocal ? { theme: null, media: {} } : loadPublished()))
      : loadPublished();
    attempt
      .then((r) => alive && setState({ status: 'ready', theme: safeTheme(r.theme), media: r.media, version: r.version ?? null }))
      // L'API du thème ne répond pas : la boutique reste ouverte avec le thème par défaut.
      .catch(() => alive && setState({ status: 'ready', theme: DEFAULT_THEME, media: {}, version: null }));
    return () => { alive = false; };
  }, [isLocal]);

  // Aperçu en direct : l'éditeur (même origine) envoie le brouillon non enregistré.
  useEffect(() => {
    if (!PREVIEW || window.parent === window) return undefined;
    const onMessage = (event) => {
      if (event.origin !== window.location.origin || event.source !== window.parent) return;
      const msg = event.data;
      if (!msg || msg.type !== PREVIEW_MESSAGE) return;
      const { value } = validateTheme(msg.theme);
      if (value) setState((s) => ({ ...s, status: 'ready', theme: value, media: { ...s.media, ...(msg.media || {}) }, version: 'draft' }));
    };
    window.addEventListener('message', onMessage);
    window.parent.postMessage({ type: `${PREVIEW_MESSAGE}:ready` }, window.location.origin);
    return () => window.removeEventListener('message', onMessage);
  }, []);

  // Réglages globaux → variables CSS (retirées en quittant la boutique, ex. vers l'administration).
  const settings = state.theme.settings;
  useEffect(() => {
    const root = document.documentElement;
    const vars = themeCssVars(settings);
    Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
    const links = fontStylesheets(settings).map((href) => {
      if (document.querySelector(`link[data-theme-font="${href}"]`)) return null;
      const link = Object.assign(document.createElement('link'), { rel: 'stylesheet', href });
      link.dataset.themeFont = href;
      document.head.appendChild(link);
      return link;
    });
    return () => {
      Object.keys(vars).forEach((k) => root.style.removeProperty(k));
      links.forEach((l) => l?.remove());
    };
  }, [settings]);

  const value = useMemo(() => ({ ...state, preview: PREVIEW }), [state]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);
