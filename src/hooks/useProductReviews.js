import { useCallback, useEffect, useState } from 'react';
import { fetchProductReviews } from '../services/contentService.js';

/** Avis approuvés d'un produit : { status, count, average, items }. Erreur réseau : section discrète (aucun avis). */
export default function useProductReviews(slug) {
  const [data, setData] = useState({ status: 'loading', count: 0, average: null, items: [] });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setData((d) => ({ ...d, status: 'loading' }));
    fetchProductReviews(slug, { signal: ctrl.signal })
      .then((d) => setData({ status: 'ready', ...d }))
      .catch(() => !ctrl.signal.aborted && setData({ status: 'error', count: 0, average: null, items: [] }));
    return () => ctrl.abort();
  }, [slug, tick]);

  const reload = useCallback(() => setTick((n) => n + 1), []);
  return { ...data, reload };
}
