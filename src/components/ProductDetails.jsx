import { useState } from 'react';
import { FileText, Leaf, Hand, Sparkles } from 'lucide-react';
import Accordion from './Accordion.jsx';
import ProductImage from './ProductImage.jsx';
import NamedIcon from './NamedIcon.jsx';
import { sanitizeRichText } from '../utils/richText.js';
import { useI18n } from '../i18n/I18nContext.jsx';

/** Description longue mise en forme (rendue seulement si elle existe ; HTML filtré). */
function RichDescription({ html }) {
  const { autoDir } = useI18n();
  if (!html) return null;
  return <div className="pdp-desc__rich" dir={autoDir} dangerouslySetInnerHTML={{ __html: sanitizeRichText(html) }} />;
}

/** Contenu des 4 rubriques, à partir des données produit existantes uniquement. */
function useSections(product) {
  const { t, autoDir } = useI18n();
  const visual = product.galleryImages.find((g) => g.fit === 'cover') || product.galleryImages[1] || product.mainImage;
  return [
    {
      id: 'description',
      title: t('pdp.tab.description'),
      body: (
        <div className="pdp-desc">
          <div className="pdp-desc__text">
            <h3 className="pdp-desc__title">{t('pdp.about')}</h3>
            <p dir={autoDir}>{product.summary}</p>
            <RichDescription html={product.descriptionHtml} />
            <p className="pdp-desc__meta"><strong>{t('pdp.skinType')}</strong> {autoDir ? <span dir={autoDir}>{product.skinTypes}</span> : product.skinTypes}</p>
          </div>
          <ProductImage image={visual} className="pdp-desc__visual" />
          <ul className="pdp-tiles pdp-tiles--wide">
            {product.highlights.map(({ icon, label }) => (
              <li key={label}><NamedIcon name={icon} size={26} strokeWidth={1.3} aria-hidden="true" /><span dir={autoDir}>{label}</span></li>
            ))}
          </ul>
        </div>
      ),
    },
    { id: 'ingredients', title: t('pdp.tab.ingredients'), body: <ul className="pdp-list">{product.ingredients.map((x) => <li key={x} dir={autoDir}>{x}</li>)}</ul> },
    { id: 'usage', title: t('pdp.tab.usage'), body: <ol className="pdp-list">{product.usage.map((x) => <li key={x} dir={autoDir}>{x}</li>)}</ol> },
    {
      id: 'benefits',
      title: t('pdp.tab.benefits'),
      body: (
        <>
          <ul className="pdp-list">{product.benefits.map((x) => <li key={x} dir={autoDir}>{x}</li>)}</ul>
          <p className="pdp-desc__meta"><strong>{t('pdp.skinType')}</strong> {autoDir ? <span dir={autoDir}>{product.skinTypes}</span> : product.skinTypes}</p>
        </>
      ),
    },
  ];
}

/** Onglets sur ordinateur ; sur mobile, une carte blanche avec les 4 rubriques repliables. */
export default function ProductDetails({ product, desktop }) {
  const sections = useSections(product);
  const { t, autoDir } = useI18n();
  const [tab, setTab] = useState('description');

  if (!desktop) {
    // Mobile : une seule carte blanche, 4 rubriques repliables (Description ouverte par défaut).
    const icons = { description: FileText, ingredients: Leaf, usage: Hand, benefits: Sparkles };
    const mobileBody = (sec) =>
      sec.id === 'description' ? (
        <>
          <h3 className="pdp-card__subtitle">{t('pdp.about')}</h3>
          <p dir={autoDir}>{product.summary}</p>
          <RichDescription html={product.descriptionHtml} />
          <p className="pdp-desc__meta"><strong>{t('pdp.skinType')}</strong> {autoDir ? <span dir={autoDir}>{product.skinTypes}</span> : product.skinTypes}</p>
        </>
      ) : sec.body;
    return (
      <section className="pdp-card" aria-label={t('pdp.info')}>
        {sections.map((sec) => (
          <Accordion key={sec.id} title={sec.title} icon={icons[sec.id]} defaultOpen={sec.id === 'description'}>
            {mobileBody(sec)}
          </Accordion>
        ))}
      </section>
    );
  }

  const current = sections.find((s) => s.id === tab);
  return (
    <section className="pdp-tabs" aria-label={t('pdp.info')}>
      <div className="pdp-tabs__list" role="tablist">
        {sections.map((s) => (
          <button key={s.id} role="tab" id={`tab-${s.id}`} aria-selected={tab === s.id} aria-controls="pdp-tabpanel" className={`pdp-tabs__tab ${tab === s.id ? 'is-active' : ''}`} onClick={() => setTab(s.id)}>
            {s.title}
          </button>
        ))}
      </div>
      <div className="pdp-tabs__panel" role="tabpanel" id="pdp-tabpanel" aria-labelledby={`tab-${tab}`}>{current.body}</div>
    </section>
  );
}
