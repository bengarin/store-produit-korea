import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Search } from 'lucide-react';
import { OTHER_CITY, searchKey } from '../data/moroccoCities.js';

const PANEL_HEIGHT = 320; // recherche + liste (260 px max, « Autre » compris)

/**
 * Sélecteur de ville (remplace la liste native) : recherche intégrée, liste compacte à défilement interne,
 * option « Autre » toujours en bas. Accessible au clavier (combobox / listbox) et compatible RTL.
 */
export default function CitySelect({
  id, value, onChange, onBlur, options, placeholder, searchPlaceholder, emptyText, otherLabel, invalid, describedBy,
}) {
  const [open, setOpen] = useState(false);
  const [up, setUp] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const root = useRef(null);
  const button = useRef(null);
  const search = useRef(null);
  const list = useRef(null);
  const listId = useId();

  const filtered = useMemo(() => {
    const q = searchKey(query);
    return q ? options.filter((o) => o.key.includes(q)) : options;
  }, [options, query]);
  const items = useMemo(() => [...filtered, { value: OTHER_CITY, label: otherLabel }], [filtered, otherLabel]);
  const selected = value === OTHER_CITY ? otherLabel : options.find((o) => o.value === value)?.label;

  const close = (refocus = true) => {
    setOpen(false);
    setQuery('');
    if (refocus) button.current?.focus();
    onBlur?.();
  };

  const openMenu = () => {
    // Ouvre vers le haut seulement s'il n'y a pas la place en dessous (et plus de place au-dessus).
    const rect = button.current.getBoundingClientRect();
    setUp(window.innerHeight - rect.bottom < PANEL_HEIGHT && rect.top > window.innerHeight - rect.bottom);
    const current = items.findIndex((o) => o.value === value);
    setActive(current >= 0 ? current : 0);
    setOpen(true);
  };

  const choose = (v) => {
    onChange(v);
    close();
  };

  // Fermeture au clic à l'extérieur.
  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (!root.current?.contains(e.target)) close(false); };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  });

  useEffect(() => { if (open) search.current?.focus(); }, [open]);
  useEffect(() => { setActive(0); }, [query]);
  useEffect(() => {
    if (open) list.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' });
  }, [active, open]);

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((i) => Math.min(i + 1, items.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)); }
    else if (e.key === 'Home') { e.preventDefault(); setActive(0); }
    else if (e.key === 'End') { e.preventDefault(); setActive(items.length - 1); }
    else if (e.key === 'Enter') { e.preventDefault(); if (items[active]) choose(items[active].value); }
    else if (e.key === 'Escape') { e.preventDefault(); close(); }
    else if (e.key === 'Tab') close(false);
  };

  const option = (o, i) => (
    <li key={o.value} id={`${listId}-${i}`} role="option" data-index={i} aria-selected={o.value === value}
      className={`city-select__option${i === active ? ' is-active' : ''}${o.value === value ? ' is-selected' : ''}${o.value === OTHER_CITY ? ' city-select__option--other' : ''}`}
      onMouseEnter={() => setActive(i)} onMouseDown={(e) => e.preventDefault()} onClick={() => choose(o.value)}>
      <span className="city-select__label">{o.label}</span>
      {o.value === value && <Check size={16} strokeWidth={2.2} aria-hidden="true" className="city-select__check" />}
    </li>
  );

  return (
    <div className={`city-select${open ? ' is-open' : ''}`} ref={root}>
      <button type="button" id={id} ref={button} className={`city-select__trigger${selected ? '' : ' is-placeholder'}`}
        aria-haspopup="listbox" aria-expanded={open} aria-controls={listId} aria-invalid={invalid || undefined}
        aria-describedby={describedBy} onClick={() => (open ? close() : openMenu())}
        onKeyDown={(e) => { if (!open && ['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) { e.preventDefault(); openMenu(); } }}>
        <span className="city-select__value">{selected || placeholder}</span>
        <ChevronDown size={18} aria-hidden="true" className="city-select__chevron" />
      </button>
      {open && (
        <div className={`city-select__panel${up ? ' is-up' : ''}`}>
          <div className="city-select__search">
            <Search size={16} aria-hidden="true" />
            <input ref={search} type="text" role="combobox" aria-expanded="true" aria-controls={listId}
              aria-activedescendant={`${listId}-${active}`} aria-autocomplete="list" aria-label={searchPlaceholder}
              placeholder={searchPlaceholder} value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={onKeyDown} />
          </div>
          <ul className="city-select__list" role="listbox" id={listId} ref={list} aria-label={placeholder}>
            {filtered.length === 0 && <li className="city-select__empty" role="presentation">{emptyText}</li>}
            {filtered.map(option)}
            {option(items[items.length - 1], items.length - 1)}
          </ul>
        </div>
      )}
    </div>
  );
}
