import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Search, X, ArrowRight } from 'lucide-react';
import ProductImage from './ProductImage.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import { formatPrice } from '../utils/currency.js';
import { unitPrice, defaultVariant } from '../utils/variants.js';

const MAX_SUGGESTIONS = 5;

/**
 * Loupe de l'en-tête : barre de recherche sous la navigation, suggestions instantanées (photo, nom, prix)
 * et « Voir tous les résultats » → /produits?q=…
 * Fermeture : Échap, clic en dehors, bouton ×, ou changement de page.
 */
export default function HeaderSearch({ placement = 'end' }) {
  const { searchProducts } = useCatalog();
  const { t } = useI18n();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(-1); // suggestion choisie au clavier
  const triggerRef = useRef(null);
  const panelRef = useRef(null);
  const inputRef = useRef(null);
  const listId = useId();

  const trimmed = query.trim();
  const results = trimmed ? searchProducts(trimmed) : [];
  const suggestions = results.slice(0, MAX_SUGGESTIONS);

  const close = () => {
    setOpen(false);
    setActive(-1);
  };

  useEffect(() => close(), [pathname, search]);

  useEffect(() => {
    if (!open) return undefined;
    inputRef.current?.focus();
    const onKey = (e) => {
      if (e.key !== 'Escape') return;
      close();
      triggerRef.current?.focus();
    };
    const onDown = (e) => {
      if (triggerRef.current?.contains(e.target) || panelRef.current?.contains(e.target)) return;
      close();
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onDown);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onDown);
    };
  }, [open]);

  const submit = (e) => {
    e.preventDefault();
    if (active >= 0 && suggestions[active]) {
      navigate(`/produits/${suggestions[active].id}`);
      return;
    }
    if (!trimmed) return;
    navigate(`/produits?q=${encodeURIComponent(trimmed)}`);
  };

  const onInputKey = (e) => {
    if (!suggestions.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((i) => (i + 1) % suggestions.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    }
  };

  return (
    <>
      <button ref={triggerRef} type="button" className={`icon-btn search-btn search-btn--${placement}`} aria-label={t('search.open')}
        aria-expanded={open} onClick={() => (open ? close() : setOpen(true))}>
        <Search size={21} strokeWidth={1.7} />
      </button>
      {open && (
        <div ref={panelRef} className="search-panel" role="search">
          <div className="search-panel__inner container">
            <form className="search-panel__form" onSubmit={submit}>
              <Search size={20} strokeWidth={1.7} aria-hidden="true" className="search-panel__icon" />
              <input
                ref={inputRef}
                type="search"
                className="search-panel__input"
                value={query}
                onChange={(e) => { setQuery(e.target.value); setActive(-1); }}
                onKeyDown={onInputKey}
                placeholder={t('search.placeholder')}
                aria-label={t('search.label')}
                role="combobox"
                aria-expanded={suggestions.length > 0}
                aria-controls={listId}
                aria-autocomplete="list"
                aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
                enterKeyHint="search"
                autoComplete="off"
                maxLength={80}
              />
              <button type="button" className="icon-btn icon-btn--sm" onClick={close} aria-label={t('search.close')}>
                <X size={20} />
              </button>
            </form>
            {trimmed && (
              <div className="search-panel__results" aria-live="polite">
                {suggestions.length ? (
                  <>
                    <ul id={listId} className="search-suggest" role="listbox" aria-label={t('search.suggestions')}>
                      {suggestions.map((p, i) => (
                        <li key={p.id} id={`${listId}-${i}`} role="option" aria-selected={i === active}>
                          <Link to={`/produits/${p.id}`} className={`search-suggest__item ${i === active ? 'is-active' : ''}`}
                            onMouseEnter={() => setActive(i)}>
                            {p.cardImage && <ProductImage image={p.cardImage} sizes="56px" className="search-suggest__img" />}
                            <span className="search-suggest__name">{p.displayName}</span>
                            <span className="search-suggest__price">{formatPrice(unitPrice(p, defaultVariant(p)))}</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                    <Link to={`/produits?q=${encodeURIComponent(trimmed)}`} className="search-panel__all">
                      {t('search.seeAll', { count: results.length })} <ArrowRight size={16} aria-hidden="true" className="search-panel__arrow" />
                    </Link>
                  </>
                ) : (
                  <p className="search-panel__empty">{t('search.empty', { query: trimmed })}</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
      {open && createPortal(<div className="search-veil" aria-hidden="true" />, document.body)}
    </>
  );
}
