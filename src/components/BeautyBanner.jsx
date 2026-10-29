import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Reveal from './Reveal.jsx';
import { getProductById } from '../data/products.js';

/** Bannière éditoriale : photo d'application réelle (SOME BY MI) + accroche. */
export default function BeautyBanner() {
  const product = getProductById('some-by-mi-yuja-niacin-cream');
  const photo = product?.galleryImages.find((g) => g.kind === 'in-use');
  return (
    <section className="home-section banner-section" aria-labelledby="banner-title">
      <Reveal className="container">
        <div className="beauty-banner">
          {photo && (
            <div className="beauty-banner__media">
              <img src={photo.src} alt={photo.alt} width="550" height="550" loading="lazy" decoding="async" />
            </div>
          )}
          <div className="beauty-banner__content">
            <p className="eyebrow">Tout en douceur</p>
            <h2 className="beauty-banner__title" id="banner-title">Révélez votre éclat naturel</h2>
            <p className="beauty-banner__text">Des soins coréens et naturels pour accompagner votre routine, jour après jour.</p>
            <Link to="/produits" className="btn btn--primary">
              Découvrir nos produits <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
