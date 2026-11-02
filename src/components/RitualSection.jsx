import { Link } from 'react-router-dom';
import { ArrowRight, ChevronRight } from 'lucide-react';
import Reveal from './Reveal.jsx';
import ProductImage from './ProductImage.jsx';
import AddToCartIcon from './AddToCartIcon.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { formatPrice } from '../utils/currency.js';
import { useI18n } from '../i18n/I18nContext.jsx';

/** Produits mis en avant (« le rituel ») : étapes du thème, chacune reliée à un produit réel du catalogue. */
export default function RitualSection({ section }) {
  const { getProductById } = useCatalog();
  const { t, tc } = useI18n();
  const [eyebrow, heading, intro] = ['eyebrow', 'heading', 'intro'].map((k) => tc(section.settings[k]));
  const titleId = `${section.id}-title`;
  // Un produit absent du catalogue (archivé, supprimé) : l'étape n'est pas affichée.
  const steps = (section.items || []).map((s) => {
    const product = getProductById(s.product);
    if (!product) return null;
    return { title: tc(s.title), text: tc(s.text), product, image: product.sceneImage };
  }).filter(Boolean).map((s, i) => ({ ...s, step: i + 1 }));
  if (!steps.length) return null;

  return (
    <section className="home-section ritual" aria-labelledby={titleId}>
      <div className="container">
        <Reveal as="header" className="section-head">
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h2 className="section-title" id={titleId}>{heading}</h2>
          {intro && <p className="section-intro">{intro}</p>}
        </Reveal>

        <ol className="ritual__steps">
          {steps.map(({ step, title, text, product, image }, i) => (
            <Reveal as="li" key={step} className="ritual-card" delay={i * 110}>
              <div className="ritual-card__head">
                <span className="ritual-card__num" aria-hidden="true">{step}</span>
                <div>
                  <h3 className="ritual-card__title"><span className="sr-only">{t('ritual.step', { step })}</span>{title}</h3>
                  {text && <p className="ritual-card__text">{text}</p>}
                </div>
                <Link to={`/produits/${product.id}`} className="ritual-card__more" aria-label={t('ritual.view', { name: product.displayName })}>
                  <ChevronRight size={18} aria-hidden="true" />
                </Link>
              </div>
              <Link to={`/produits/${product.id}`} className="ritual-card__media" tabIndex={-1} aria-hidden="true">
                <ProductImage image={image} />
              </Link>
              <div className="ritual-card__product">
                <Link to={`/produits/${product.id}`} className="ritual-card__thumb" tabIndex={-1} aria-hidden="true">
                  <ProductImage image={product.cardImage} />
                </Link>
                <div className="ritual-card__info">
                  <Link to={`/produits/${product.id}`} className="ritual-card__name">{product.displayName}</Link>
                  <span className="ritual-card__price">{formatPrice(product.price)}</span>
                </div>
                <AddToCartIcon product={product} />
              </div>
              {i < steps.length - 1 && <span className="ritual-card__arrow" aria-hidden="true"><ArrowRight size={18} /></span>}
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
