import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ProductCard from './ProductCard.jsx';
import { useCart } from '../context/CartContext.jsx';
import useQuickAdd from '../hooks/useQuickAdd.js';

const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

/**
 * Carrousel natif (scroll-snap) : glisser au doigt sur mobile, flèches sur desktop.
 * 1 carte visible (mobile) → 2 (tablette) → 3 (desktop), défini en CSS.
 */
export default function ProductCarousel({ products, label = 'Produits' }) {
  const track = useRef(null);
  const frame = useRef(0);
  const [state, setState] = useState({ index: 0, pages: 1, atStart: true, atEnd: false });
  const { favorites, toggleFavorite } = useCart();
  const handleAdd = useQuickAdd();

  const measure = useCallback(() => {
    const el = track.current;
    if (!el || !el.firstElementChild) return;
    const gap = parseFloat(getComputedStyle(el).columnGap) || 0;
    const step = el.firstElementChild.getBoundingClientRect().width + gap;
    const perView = Math.max(1, Math.round((el.clientWidth + gap) / step));
    setState({
      index: Math.round(el.scrollLeft / step),
      pages: Math.max(1, products.length - perView + 1),
      atStart: el.scrollLeft < 4,
      atEnd: el.scrollLeft + el.clientWidth >= el.scrollWidth - 4,
    });
  }, [products.length]);

  useEffect(() => {
    measure();
    window.addEventListener('resize', measure);
    return () => {
      window.removeEventListener('resize', measure);
      cancelAnimationFrame(frame.current);
    };
  }, [measure]);

  const onScroll = () => {
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(measure);
  };

  const goTo = (i) => {
    const el = track.current;
    const card = el?.children[i];
    if (!card) return;
    el.scrollTo({ left: card.offsetLeft - el.firstElementChild.offsetLeft, behavior: reduceMotion() ? 'auto' : 'smooth' });
  };

  return (
    <div className="carousel" role="region" aria-roledescription="carrousel" aria-label={label}>
      <button className="carousel__arrow carousel__arrow--prev" onClick={() => goTo(Math.max(0, state.index - 1))} disabled={state.atStart} aria-label="Produits précédents">
        <ChevronLeft size={20} />
      </button>
      <div className="carousel__track" ref={track} onScroll={onScroll} tabIndex={0}>
        {products.map((p, i) => (
          <div className="carousel__slide" key={p.id} role="group" aria-roledescription="diapositive" aria-label={`${i + 1} sur ${products.length}`}>
            <ProductCard product={p} variant="scene" animate={false} isFavorite={favorites.includes(p.id)} onToggleFavorite={toggleFavorite} onAdd={handleAdd} />
          </div>
        ))}
      </div>
      <button className="carousel__arrow carousel__arrow--next" onClick={() => goTo(Math.min(products.length - 1, state.index + 1))} disabled={state.atEnd} aria-label="Produits suivants">
        <ChevronRight size={20} />
      </button>
      {state.pages > 1 && (
        <div className="carousel__dots">
          {Array.from({ length: state.pages }, (_, i) => (
            <button key={i} className={`carousel__dot ${i === Math.min(state.index, state.pages - 1) ? 'is-active' : ''}`} onClick={() => goTo(i)} aria-label={`Aller à la position ${i + 1}`} aria-current={i === state.index ? 'true' : undefined} />
          ))}
        </div>
      )}
    </div>
  );
}
