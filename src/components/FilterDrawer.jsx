import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { useI18n } from '../i18n/I18nContext.jsx';
import FilterPanel from './FilterPanel.jsx';

/**
 * Filtres sur mobile : tiroir plein écran (côté de lecture : gauche en français, droite en arabe).
 * Les choix restent en brouillon ; « Appliquer » les envoie (le bouton indique le nombre de produits).
 */
export default function FilterDrawer({ open, onClose, applied, empty, onApply, countFor, panelProps }) {
  const { t } = useI18n();
  const [draft, setDraft] = useState(applied);

  useEffect(() => {
    if (!open) return undefined;
    setDraft(applied);
    const onKey = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- le brouillon repart des filtres appliqués à chaque ouverture
  }, [open]);

  if (!open) return null;
  const count = countFor(draft);
  return createPortal(
    <div className="filter-drawer" role="dialog" aria-modal="true" aria-labelledby="filter-drawer-title">
      <button type="button" className="filter-drawer__backdrop" onClick={onClose} aria-label={t('filters.close')} tabIndex={-1} />
      <div className="filter-drawer__panel">
        <header className="filter-drawer__head">
          <h2 id="filter-drawer-title">{t('filters.title')}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t('filters.close')} autoFocus>
            <X size={22} />
          </button>
        </header>
        <div className="filter-drawer__body">
          <FilterPanel {...panelProps(draft)} state={draft} onChange={setDraft} live={false} />
        </div>
        <footer className="filter-drawer__foot">
          <button type="button" className="btn btn--outline" onClick={() => setDraft({ ...empty, sort: draft.sort })}>{t('filters.reset')}</button>
          <button type="button" className="btn btn--primary" onClick={() => onApply(draft)}>
            {t('filters.apply', { count })}
          </button>
        </footer>
      </div>
    </div>,
    document.body,
  );
}
