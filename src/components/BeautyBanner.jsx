import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Reveal from './Reveal.jsx';
import desktopImg from '../assets/banner/eclat-desktop.webp';
import desktopImg1200 from '../assets/banner/eclat-desktop-1200.webp';
import mobileImg from '../assets/banner/eclat-mobile.webp';
import mobileImg640 from '../assets/banner/eclat-mobile-640.webp';

/**
 * Bannière « Révélez votre éclat naturel ».
 * - ≥ 860 px : image horizontale (portrait à gauche), texte posé sur la zone beige de droite.
 * - < 860 px : image verticale (zone beige en haut), texte au-dessus du portrait.
 */
export default function BeautyBanner() {
  return (
    <section className="home-section banner-section" aria-labelledby="banner-title">
      <Reveal className="container">
        <div className="beauty-banner">
          <picture className="beauty-banner__media">
            <source media="(min-width: 860px)" srcSet={`${desktopImg1200} 1200w, ${desktopImg} 1920w`} sizes="min(100vw, 1200px)" width="1920" height="768" />
            <img
              src={mobileImg640}
              srcSet={`${mobileImg640} 640w, ${mobileImg} 890w`}
              sizes="(max-width: 520px) 100vw, 520px"
              width="890"
              height="1767"
              alt="Portrait d’une femme au teint lumineux, la main posée sur la joue"
              loading="lazy"
              decoding="async"
            />
          </picture>
          <div className="beauty-banner__content">
            <p className="beauty-banner__eyebrow">Tout en douceur</p>
            <h2 className="beauty-banner__title" id="banner-title">Révélez votre éclat naturel</h2>
            <p className="beauty-banner__text">Des soins coréens et naturels pour accompagner votre routine, jour après jour.</p>
            <Link to="/produits" className="btn btn--primary beauty-banner__btn">
              Découvrir nos produits <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
