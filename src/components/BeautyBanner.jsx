import { ArrowRight } from 'lucide-react';
import Reveal from './Reveal.jsx';
import ThemeLink from '../theme/ThemeLink.jsx';
import { resolveImage } from '../theme/assets.js';
import { useTheme } from '../theme/ThemeContext.jsx';

/**
 * Bannière promotionnelle (section « promo_banner » du thème ; à l'origine « Révélez votre éclat naturel »).
 * - ≥ 860 px : image horizontale, texte posé sur la zone claire de droite.
 * - < 860 px : image verticale, texte au-dessus.
 */
export default function BeautyBanner({ section }) {
  const { media } = useTheme();
  const { eyebrow, heading, text, buttonLabel, buttonLink, imageDesktop, imageMobile, imageAlt } = section.settings;
  const desktop = resolveImage(imageDesktop, media);
  const mobile = resolveImage(imageMobile, media) || desktop;
  const titleId = `${section.id}-title`;
  return (
    <section className="home-section banner-section" aria-labelledby={titleId}>
      <Reveal className="container">
        <div className="beauty-banner">
          {mobile && (
            <picture className="beauty-banner__media">
              {desktop && desktop !== mobile && (
                <source media="(min-width: 860px)" srcSet={desktop.srcSet || desktop.src} sizes="min(100vw, 1200px)" width={desktop.width} height={desktop.height} />
              )}
              <img
                src={mobile.src}
                srcSet={mobile.srcSet}
                sizes="(max-width: 520px) 100vw, 520px"
                width={mobile.width}
                height={mobile.height}
                alt={imageAlt}
                loading="lazy"
                decoding="async"
              />
            </picture>
          )}
          <div className="beauty-banner__content">
            {eyebrow && <p className="beauty-banner__eyebrow">{eyebrow}</p>}
            <h2 className="beauty-banner__title" id={titleId}>{heading}</h2>
            {text && <p className="beauty-banner__text">{text}</p>}
            {buttonLabel && buttonLink && (
              <ThemeLink to={buttonLink} className="btn btn--primary beauty-banner__btn">
                {buttonLabel} <ArrowRight size={16} aria-hidden="true" />
              </ThemeLink>
            )}
          </div>
        </div>
      </Reveal>
    </section>
  );
}
