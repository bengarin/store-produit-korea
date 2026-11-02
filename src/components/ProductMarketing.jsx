import Reveal from './Reveal.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import { marketingFor } from '../services/productService.js';

// Ordre des sections de la « landing page » ; une section sans visuel n'est jamais affichée.
const ORDER = ['banner', 'benefits', 'ingredients', 'usage', 'before_after', 'comparison', 'brand', 'other'];

function MarketingVisual({ item, eager }) {
  const { autoDir } = useI18n();
  return (
    <figure className="pdp-mkt__card">
      <img
        src={item.src640 || item.src}
        srcSet={item.src640 ? `${item.src640} 640w, ${item.src} ${item.width}w` : undefined}
        sizes="(min-width: 860px) 46vw, 100vw"
        width={item.width}
        height={item.height}
        alt={item.alt || ''}
        loading={eager ? 'eager' : 'lazy'}
        decoding="async"
      />
      {(item.title || item.description) && (
        <figcaption className="pdp-mkt__caption" dir={autoDir}>
          {item.title && <strong>{item.title}</strong>}
          {item.description && <span>{item.description}</span>}
        </figcaption>
      )}
    </figure>
  );
}

/**
 * Visuels marketing du produit, regroupés par catégorie (colonne de droite sur ordinateur, sous les
 * informations sur mobile). Distincts des photos du produit (galerie) : aucun mélange.
 */
export default function ProductMarketing({ product }) {
  const { t, lang } = useI18n();
  const items = marketingFor(product, lang);
  if (!items.length) return null;
  const groups = ORDER.map((category) => [category, items.filter((m) => m.category === category)]).filter(([, list]) => list.length);
  return (
    <div className="pdp-mkt" aria-label={t('mkt.label')}>
      {groups.map(([category, list], g) => (
        <Reveal as="section" key={category} className={`pdp-mkt__section pdp-mkt__section--${category}`} aria-labelledby={`mkt-${category}`}>
          <h2 className="pdp-mkt__title" id={`mkt-${category}`}>{t(`mkt.${category}`)}</h2>
          <div className="pdp-mkt__list">
            {list.map((item, i) => <MarketingVisual key={item.id} item={item} eager={g === 0 && i === 0} />)}
          </div>
          {category === 'before_after' && <p className="pdp-mkt__note">{t('mkt.beforeAfterNote')}</p>}
        </Reveal>
      ))}
    </div>
  );
}
