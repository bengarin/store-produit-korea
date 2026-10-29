import { useId, useState } from 'react';
import { ChevronDown } from 'lucide-react';

export default function Accordion({ title, children, defaultOpen = false, icon: Icon = null }) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();
  return (
    <div className={`accordion ${open ? 'is-open' : ''}`}>
      <button className="accordion__trigger" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls={id}>
        {Icon && <Icon className="accordion__icon" size={24} strokeWidth={1.4} aria-hidden="true" />}
        <span className="accordion__title">{title}</span>
        <ChevronDown className="accordion__chevron" size={20} aria-hidden="true" />
      </button>
      <div id={id} className="accordion__panel" hidden={!open}>
        {children}
      </div>
    </div>
  );
}
