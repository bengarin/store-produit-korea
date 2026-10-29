import { Link } from 'react-router-dom';
import { ArrowRight, ChevronRight } from 'lucide-react';
import Reveal from './Reveal.jsx';
import ProductImage from './ProductImage.jsx';
import AddToCartIcon from './AddToCartIcon.jsx';
import { RITUAL_STEPS } from '../data/ritual.js';
import { useCatalog } from '../context/CatalogContext.jsx';
import { formatPrice } from '../utils/currency.js';

export default function RitualSection() {
  const { getProductById } = useCatalog();
  const steps = RITUAL_STEPS.map((s) => {
    const product = getProductById(s.productId);
    if (!product) return null;
    return { ...s, product, image: product.sceneImage };
  }).filter(Boolean);

  return (
    <section className="home-section ritual" aria-labelledby="ritual-title">
      <div className="container">
        <Reveal as="header" className="section-head">
          <p className="eyebrow">Votre routine beauté</p>
          <h2 className="section-title" id="ritual-title">Le rituel NATURE</h2>
          <p className="section-intro">Trois étapes simples, trois soins, une seule sélection.</p>
        </Reveal>

        <ol className="ritual__steps">
          {steps.map(({ step, title, text, product, image }, i) => (
            <Reveal as="li" key={step} className="ritual-card" delay={i * 110}>
              <div className="ritual-card__head">
                <span className="ritual-card__num" aria-hidden="true">{step}</span>
                <div>
                  <h3 className="ritual-card__title"><span className="sr-only">Étape {step} : </span>{title}</h3>
                  <p className="ritual-card__text">{text}</p>
                </div>
                <Link to={`/produits/${product.id}`} className="ritual-card__more" aria-label={`Voir ${product.displayName}`}>
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
