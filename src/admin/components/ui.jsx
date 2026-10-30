import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, ChevronLeft, ChevronRight, Inbox, Loader2, RefreshCw, X } from 'lucide-react';
import { ORDER_STATUS, PAYMENT_STATUS, STOCK_STATE, formatInt } from '../format.js';

export function Button({ variant = 'primary', size, icon: Icon, loading = false, children, className = '', ...props }) {
  return (
    <button
      type="button"
      className={`adm-btn adm-btn--${variant} ${size ? `adm-btn--${size}` : ''} ${className}`}
      disabled={loading || props.disabled}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <Loader2 size={16} className="adm-spin" aria-hidden="true" /> : Icon && <Icon size={16} aria-hidden="true" />}
      {children && <span>{children}</span>}
    </button>
  );
}

export function ButtonLink({ variant = 'secondary', icon: Icon, children, className = '', ...props }) {
  const Tag = props.to ? Link : 'a';
  return (
    <Tag className={`adm-btn adm-btn--${variant} ${className}`} {...props}>
      {Icon && <Icon size={16} aria-hidden="true" />}
      <span>{children}</span>
    </Tag>
  );
}

export function Badge({ tone = 'neutral', children }) {
  return <span className={`adm-badge adm-badge--${tone}`}>{children}</span>;
}

export const StatusBadge = ({ status }) => {
  const s = ORDER_STATUS[status] || { label: status, tone: 'neutral' };
  return <Badge tone={s.tone}>{s.label}</Badge>;
};
export const PaymentBadge = ({ status }) => {
  const s = PAYMENT_STATUS[status] || { label: status, tone: 'neutral' };
  return <Badge tone={s.tone}>{s.label}</Badge>;
};
export const StockBadge = ({ state }) => {
  const s = STOCK_STATE[state] || { label: state, tone: 'neutral' };
  return <Badge tone={s.tone}>{s.label}</Badge>;
};

export function Card({ title, actions, children, className = '', padded = true }) {
  return (
    <section className={`adm-card ${padded ? '' : 'adm-card--flush'} ${className}`}>
      {(title || actions) && (
        <header className="adm-card__head">
          {title && <h2 className="adm-card__title">{title}</h2>}
          {actions && <div className="adm-card__actions">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function PageHeader({ title, subtitle, actions, back, badge }) {
  return (
    <header className="adm-page-head">
      {back && (
        <Link to={back.to} className="adm-back"><ArrowLeft size={16} aria-hidden="true" /> {back.label}</Link>
      )}
      <div className="adm-page-head__row">
        <div className="adm-page-head__text">
          <h1>{title} {badge}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions && <div className="adm-page-head__actions">{actions}</div>}
      </div>
    </header>
  );
}

export function PageLoader({ label = 'Chargement…' }) {
  return (
    <div className="adm-loader" role="status">
      <Loader2 size={22} className="adm-spin" aria-hidden="true" /> <span>{label}</span>
    </div>
  );
}

export function SkeletonRows({ rows = 5 }) {
  return (
    <div className="adm-skeleton" aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => <span key={i} />)}
    </div>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, text, action }) {
  return (
    <div className="adm-empty">
      <span className="adm-empty__icon"><Icon size={26} strokeWidth={1.5} aria-hidden="true" /></span>
      <h3>{title}</h3>
      {text && <p>{text}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  const forbidden = error?.status === 403;
  return (
    <div className="adm-error" role="alert">
      <AlertTriangle size={20} aria-hidden="true" />
      <div>
        <strong>{forbidden ? 'Accès refusé' : 'Impossible de charger les données'}</strong>
        <p>{forbidden ? 'Votre rôle ne permet pas d’accéder à cette page.' : error?.message}</p>
      </div>
      {onRetry && !forbidden && <Button variant="secondary" size="sm" icon={RefreshCw} onClick={onRetry}>Réessayer</Button>}
    </div>
  );
}

export function Notice({ tone = 'info', icon: Icon = AlertTriangle, children, action }) {
  return (
    <div className={`adm-notice adm-notice--${tone}`}>
      <Icon size={18} aria-hidden="true" />
      <div className="adm-notice__body">{children}</div>
      {action}
    </div>
  );
}

export function Pagination({ page, pageSize, total, onChange }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) return total ? <p className="adm-pagination__info">{formatInt(total)} résultat{total > 1 ? 's' : ''}</p> : null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <nav className="adm-pagination" aria-label="Pagination">
      <p className="adm-pagination__info">{from}–{to} sur {formatInt(total)}</p>
      <div>
        <Button variant="secondary" size="sm" icon={ChevronLeft} disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Page précédente" />
        <span className="adm-pagination__page">Page {page} / {pages}</span>
        <Button variant="secondary" size="sm" icon={ChevronRight} disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="Page suivante" />
      </div>
    </nav>
  );
}

/** Fenêtre modale accessible (Échap, focus initial, focus rendu à la fermeture). */
export function Modal({ open, title, onClose, children, footer, size = 'md' }) {
  const titleId = useId();
  const panelRef = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    const onKey = (e) => e.key === 'Escape' && onClose?.();
    document.addEventListener('keydown', onKey);
    const focusable = panelRef.current?.querySelector('input, select, textarea, button:not(.adm-modal__close)');
    (focusable || panelRef.current)?.focus();
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
      previous?.focus?.();
    };
  }, [open, onClose]);
  if (!open) return null;
  return createPortal(
    <div className="adm-modal" role="presentation">
      <button type="button" className="adm-modal__backdrop" aria-label="Fermer" tabIndex={-1} onClick={onClose} />
      <div className={`adm-modal__panel adm-modal__panel--${size}`} role="dialog" aria-modal="true" aria-labelledby={titleId}
        ref={panelRef} tabIndex={-1}>
        <header className="adm-modal__head">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="adm-modal__close" onClick={onClose} aria-label="Fermer"><X size={18} /></button>
        </header>
        <div className="adm-modal__body">{children}</div>
        {footer && <footer className="adm-modal__foot">{footer}</footer>}
      </div>
    </div>,
    document.body,
  );
}

export function Field({ label, hint, error, children, htmlFor, required }) {
  return (
    <div className={`adm-field ${error ? 'has-error' : ''}`}>
      {label && (
        <label htmlFor={htmlFor}>{label}{required && <span className="adm-req" aria-hidden="true"> *</span>}</label>
      )}
      {children}
      {hint && !error && <p className="adm-field__hint">{hint}</p>}
      {error && <p className="adm-field__error" role="alert">{error}</p>}
    </div>
  );
}
