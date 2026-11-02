import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Reveal from './Reveal.jsx';
import ProductCarousel from './ProductCarousel.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { STORE_CONFIG } from '../config/store.js';

/** Collection de produits (carrousel) : tout le catalogue ou une catégorie. {nombre} = nombre de produits. */
export default function ProductCollection({ section }) {
  const { products } = useCatalog();
  const { eyebrow, heading, intro, category, viewAllLabel } = section.settings;
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
        {STORE_CONFIG.showDemoNotices && <p className="demo-note">Prix provisoires — à confirmer avant la mise en ligne.</p>}
      </div>
    </section>
  );
}
