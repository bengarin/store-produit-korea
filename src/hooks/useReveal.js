import { useEffect, useRef, useState } from 'react';

const reduceMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

/**
 * Apparition au défilement : renvoie [ref, visible].
 * - visible passe à true la première fois que l'élément entre dans l'écran, puis ne bouge plus.
 * - Sans IntersectionObserver ou avec « réduire les animations » : visible tout de suite.
 */
export default function useReveal({ rootMargin = '0px 0px -8% 0px' } = {}) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(() => typeof IntersectionObserver === 'undefined' || reduceMotion());

  useEffect(() => {
    if (visible || !ref.current) return undefined;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          io.disconnect();
        }
      },
      { rootMargin, threshold: 0.12 },
    );
    io.observe(ref.current);
    return () => io.disconnect();
  }, [visible, rootMargin]);

  return [ref, visible];
}
