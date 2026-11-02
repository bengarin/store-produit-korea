import { ArrowRight } from 'lucide-react';
import Reveal from './Reveal.jsx';
import ThemeLink from '../theme/ThemeLink.jsx';
import { resolveImage } from '../theme/assets.js';
import { useTheme } from '../theme/ThemeContext.jsx';

/** Texte et image (section « image_with_text ») : textes affichés tels quels, sans HTML. */
export default function ImageWithText({ section }) {
  const { media } = useTheme();
  const { image, imageAlt, imagePosition, eyebrow, heading, text, buttonLabel, buttonLink, background } = section.settings;
  const img = resolveImage(image, media);
  const titleId = `${section.id}-title`;
  const paragraphs = (text || '').split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
  return (
    <section className={`home-section iwt iwt--${background}${imagePosition === 'right' ? ' iwt--reverse' : ''}`} aria-labelledby={titleId}>
      <div className="container iwt__inner">
        {img && (
          <Reveal className="iwt__media">
            <img src={img.src} srcSet={img.srcSet} sizes="(min-width: 860px) 50vw, 100vw" width={img.width} height={img.height}
              alt={imageAlt} loading="lazy" decoding="async" />
          </Reveal>
        )}
        <Reveal className="iwt__content">
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h2 className="iwt__title" id={titleId}>{heading}</h2>
          {paragraphs.map((p, i) => <p key={i} className="iwt__text">{p}</p>)}
          {buttonLabel && buttonLink && (
            <ThemeLink to={buttonLink} className="btn btn--primary iwt__btn">
              {buttonLabel} <ArrowRight size={16} aria-hidden="true" />
            </ThemeLink>
          )}
        </Reveal>
      </div>
    </section>
  );
}
