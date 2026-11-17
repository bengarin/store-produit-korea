import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import ProductImage from './ProductImage.jsx';
import Reveal from './Reveal.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

/**
 * Accueil : une carte par collection (Admin → Collections) — image, description courte, « Découvrir la collection ».
 * Rien n'est affiché tant qu'aucune collection ne contient de produit en ligne.
 */
export default function CollectionCards() {
  const { collections } = useCatalog();
  const { t } = useI18n();
  if (!collections.length) return null;
  return (
    <section className="section collections-home" aria-labelledby="collections-home-title">
      <div className="container">
        <header className="section-head">
          <p className="eyebrow">{t('collections.eyebrowHome')}</p>
          <h2 id="collections-home-title" className="section-title">{t('collections.title')}</h2>
        </header>
        <ul className={`collection-cards collection-cards--${Math.min(collections.length, 3)}`}>
          {collections.map((c) => (
            <li key={c.id}>
              <Reveal>
                <article className="collection-card">
                  <Link to={`/collections/${encodeURIComponent(c.id)}`} className="collection-card__media" tabIndex={-1} aria-hidden="true">
                    {c.image
                      ? <ProductImage image={c.image} sizes="(min-width: 900px) 45vw, 92vw" className="collection-card__img" />
                      : <span className="collection-card__placeholder" />}
                  </Link>
                  <div className="collection-card__body">
                    <h3 className="collection-card__title">{c.label}</h3>
                    {c.description && <p className="collection-card__text">{c.description}</p>}
                    <Link to={`/collections/${encodeURIComponent(c.id)}`} className="btn btn--primary collection-card__cta"
                      aria-label={`${t('collections.discover')} : ${c.label}`}>
                      {t('collections.discover')} <ArrowRight size={17} aria-hidden="true" className="collection-card__arrow" />
                    </Link>
                  </div>
                </article>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
