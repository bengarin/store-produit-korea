import { useNavigate } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';

/** En-tête simple : retour + titre + action optionnelle à droite. */
export default function PageHeader({ title, fallback = '/', right = null }) {
  const navigate = useNavigate();
  const goBack = () => (window.history.state?.idx > 0 ? navigate(-1) : navigate(fallback));

  return (
    <header className="page-header">
      <div className="page-header__inner container">
        <button className="icon-btn" onClick={goBack} aria-label="Retour">
          <ChevronLeft size={26} strokeWidth={1.6} />
        </button>
        <h1 className="page-header__title">{title}</h1>
        <div className="page-header__right">{right}</div>
      </div>
    </header>
  );
}
