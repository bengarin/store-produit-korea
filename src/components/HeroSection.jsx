import { ArrowDown, ArrowRight } from 'lucide-react';
import ThemeLink from '../theme/ThemeLink.jsx';
import { resolveImage } from '../theme/assets.js';
import { useTheme } from '../theme/ThemeContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

/**
 * Une bannière (texte modifiable posé sur l'image, jamais incrusté dedans).
 * Utilisée seule (bannière fixe) ET pour chaque diapositive du carrousel : rendu identique.
 * `first` : la 1re bannière porte le titre <h1> de la page et charge son image en priorité.
 */
export function HeroSlideView({ slide, titleId, first = true }) {
  const { eyebrow, heading, text, buttonLabel, buttonLink, desktop, mobile: mobileImage, imageAlt } = slide;
  const mobile = mobileImage || desktop;
  const Arrow = buttonLink?.startsWith('#') ? ArrowDown : ArrowRight;
  const Title = first ? 'h1' : 'h2';

  return (
    <div className="hero__inner">
      <div className="hero__copy">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <Title id={titleId} className="hero__title">{heading}</Title>
        {text && <p className="hero__text">{text}</p>}
        {buttonLabel && buttonLink && (
          <ThemeLink to={buttonLink} className="btn btn--primary btn--lg">
            {buttonLabel} <Arrow size={17} />
          </ThemeLink>
        )}
      </div>
      {/* Visuel produit : image entière, jamais étirée ; seul le mur vide du haut se fond dans le crème. */}
      {mobile && (
        <div className="hero__visual">
          <picture>
            {/* Desktop (≥ 1000 px) : visuel paysage ; mobile : visuel portrait. */}
            {desktop && desktop !== mobile && (
              <source media="(min-width: 1000px)" srcSet={desktop.srcSet || desktop.src} sizes="min(100vw, 1600px)" width={desktop.width} height={desktop.height} />
            )}
            <img
              src={mobile.src}
              srcSet={mobile.srcSet}
              sizes="(min-width: 900px) 46vw, (min-width: 600px) 520px, 100vw"
              width={mobile.width}
              height={mobile.height}
              alt={imageAlt}
              fetchpriority={first ? 'high' : undefined}
              loading={first ? undefined : 'lazy'}
              decoding="async"
            />
          </picture>
        </div>
      )}
    </div>
  );
}

/** Bannière principale de l'accueil (section « hero » du thème) : utilisée sans diapositives (mode démo, aperçu du thème). */
export default function HeroSection({ section }) {
  const { media } = useTheme();
  const { tc } = useI18n();
  const { buttonLink, imageDesktop, imageMobile } = section.settings;
  const [eyebrow, heading, text, buttonLabel, imageAlt] = ['eyebrow', 'heading', 'text', 'buttonLabel', 'imageAlt'].map((k) => tc(section.settings[k]));
  const desktop = resolveImage(imageDesktop, media);
  const mobile = resolveImage(imageMobile, media) || desktop;
  const titleId = `${section.id}-title`;

  return (
    <section className="hero" aria-labelledby={titleId}>
      <HeroSlideView titleId={titleId} slide={{ eyebrow, heading, text, buttonLabel, buttonLink, desktop, mobile, imageAlt }} />
    </section>
  );
}
