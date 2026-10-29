import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/** Remonte en haut à chaque page ; descend jusqu'à l'ancre si l'URL a un #. */
export default function ScrollToTop() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (hash) {
      const t = setTimeout(() => document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' }), 0);
      return () => clearTimeout(t);
    }
    window.scrollTo(0, 0);
    return undefined;
  }, [pathname, hash]);
  return null;
}
