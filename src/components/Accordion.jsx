import { useId, useState } from 'react';
import { ChevronDown } from 'lucide-react';

export default function Accordion({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();
  return (
    <div className={`accordion ${open ? 'is-open' : ''}`}>
      <button className="accordion__trigger" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls={id}>
        <span>{title}</span>
        <ChevronDown size={18} />
      </button>
      <div id={id} className="accordion__panel" hidden={!open}>
        {children}
      </div>
    </div>
  );
}
