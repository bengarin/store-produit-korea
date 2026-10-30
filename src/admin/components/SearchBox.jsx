import { useEffect, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';

/** Recherche validée par Entrée ou après une courte pause de frappe. */
export default function SearchBox({ value, onChange, placeholder, label = 'Rechercher' }) {
  const [text, setText] = useState(value || '');
  // Toujours la dernière version de onChange : évite d'effacer un filtre choisi pendant la frappe.
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  useEffect(() => setText(value || ''), [value]);
  useEffect(() => {
    if (text === (value || '')) return undefined;
    const t = setTimeout(() => onChangeRef.current(text.trim()), 400);
    return () => clearTimeout(t);
  }, [text]); // eslint-disable-line react-hooks/exhaustive-deps -- déclenché par la frappe uniquement
  return (
    <form className="adm-search" role="search" onSubmit={(e) => { e.preventDefault(); onChange(text.trim()); }}>
      <Search size={16} aria-hidden="true" />
      <input type="search" className="adm-input" value={text} placeholder={placeholder} aria-label={label}
        onChange={(e) => setText(e.target.value)} />
      {text && (
        <button type="button" className="adm-search__clear" aria-label="Effacer la recherche" onClick={() => { setText(''); onChange(''); }}>
          <X size={14} />
        </button>
      )}
    </form>
  );
}
