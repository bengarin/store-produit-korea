import { useNavigate } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { useI18n } from '../i18n/I18nContext.jsx';

/** En-tête simple : retour + titre + action optionnelle à droite. */
export default function PageHeader({ title, fallback = '/', right = null }) {
  const navigate = useNavigate();
  const { t } = useI18n();
  const goBack = () => (window.history.state?.idx > 0 ? navigate(-1) : navigate(fallback));

  return (
    <header className="page-header">
      <div className="page-header__inner container">
        <button className="icon-btn" onClick={goBack} aria-label={t('common.back')}>
          <ChevronLeft size={26} strokeWidth={1.6} />
        </button>
        <h1 className="page-header__title">{title}</h1>
        <div className="page-header__right">{right}</div>
      </div>
    </header>
  );
}
