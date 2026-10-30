import { useEffect, useId, useRef, useState } from 'react';
import { MoreHorizontal } from 'lucide-react';

/** Menu d'actions rapides d'une ligne (clavier : Échap pour fermer, flèches pour naviguer). */
export default function RowMenu({ label, items }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const id = useId();
  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => !ref.current?.contains(e.target) && setOpen(false);
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false);
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        const buttons = [...ref.current.querySelectorAll('[role=menuitem]:not(:disabled)')];
        const i = buttons.indexOf(document.activeElement);
        buttons[(i + (e.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length]?.focus();
        e.preventDefault();
      }
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    ref.current.querySelector('[role=menuitem]')?.focus();
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);
  const visible = items.filter(Boolean);
  if (!visible.length) return null;
  return (
    <div className="adm-menu" ref={ref} onClick={(e) => e.stopPropagation()}>
      <button type="button" className="adm-icon-btn" aria-label={label} aria-haspopup="menu" aria-expanded={open}
        aria-controls={id} onClick={() => setOpen((v) => !v)}>
        <MoreHorizontal size={18} />
      </button>
      {open && (
        <div className="adm-menu__list" role="menu" id={id}>
          {visible.map((item) => (
            <button key={item.label} type="button" role="menuitem" className={item.danger ? 'is-danger' : ''}
              onClick={() => { setOpen(false); item.onClick(); }}>
              {item.icon && <item.icon size={15} aria-hidden="true" />} {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
