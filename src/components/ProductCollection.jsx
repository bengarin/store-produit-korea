import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Reveal from './Reveal.jsx';
import ProductCarousel from './ProductCarousel.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { STORE_CONFIG } from '../config/store.js';
import { useI18n } from '../i18n/I18nContext.jsx';

/** Collection de produits (carrousel) : tout le catalogue ou une catégorie. {nombre} = nombre de produits. */
export default function ProductCollection({ section }) {
  const { products } = useCatalog();
  const { t, tc } = useI18n();
  const { category } = section.settings;
  const [eyebrow, heading, intro, viewAllLabel] = ['eyebrow', 'heading', 'intro', 'viewAllLabel'].map((k) => tc(section.settings[k]));
  const list = category ? products.filter((p) => p.categories.includes(category)) : products;
  if (!list.length) return null;
  const titleId = `${section.id}-title`;
  return (
    <section className="home-section moment" id={section.id} aria-labelledby={titleId}>
      <div className="container">
        <Reveal as="header" className="section-head section-head--split">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            <h2 className="section-title" id={titleId}>{heading}</h2>
            {intro && <p className="section-intro">{intro.replaceAll('{nombre}', String(list.length))}</p>}
          </div>
          {viewAllLabel && (
            <Link to={category ? `/produits?categorie=${encodeURIComponent(category)}` : '/produits'} className="text-arrow">
              {viewAllLabel} <ArrowRight size={16} aria-hidden="true" />
            </Link>
          )}
        </Reveal>
        <Reveal>
          <ProductCarousel products={list} label={heading} />
        </Reveal>
        {STORE_CONFIG.showDemoNotices && <p className="demo-note">{t('demo.prices')}</p>}
      </div>
    </section>
  );
}
