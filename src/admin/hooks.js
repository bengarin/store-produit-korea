import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { adminRequest } from './api.js';

/** Charge une ressource admin. Garde les anciennes données pendant un rechargement (filtres). */
export function useApi(path, params = null, { enabled = true } = {}) {
  const key = JSON.stringify([path, params]);
  const [state, setState] = useState({ data: null, error: null, loading: Boolean(enabled && path) });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!enabled || !path) return undefined;
    const controller = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    adminRequest(path, { params: params || undefined, signal: controller.signal })
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (!controller.signal.aborted) setState((s) => ({ ...s, error, loading: false }));
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `key` résume path + params
  }, [key, tick, enabled]);

  const reload = useCallback(() => setTick((n) => n + 1), []);
  return { ...state, reload, setData: (data) => setState((s) => ({ ...s, data })) };
}

/** Filtres stockés dans l'URL (partageables, conservés au retour arrière). */
export function useUrlFilters(defaults = {}) {
  const [params, setParams] = useSearchParams();
  const values = useMemo(() => {
    const out = { ...defaults };
    params.forEach((value, name) => { out[name] = value; });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- defaults est une constante de la page
  }, [params]);
  const update = useCallback((changes, { resetPage = true } = {}) => {
    const next = new URLSearchParams(params);
    Object.entries({ ...(resetPage ? { page: '' } : {}), ...changes }).forEach(([name, value]) => {
      if (value === '' || value === null || value === undefined) next.delete(name);
      else next.set(name, value);
    });
    setParams(next, { replace: true });
  }, [params, setParams]);
  return [values, update];
}

/** Titre de l'onglet. */
export function useTitle(title) {
  useEffect(() => {
    document.title = `${title} · Admin Ma Petite Corée`;
  }, [title]);
}
