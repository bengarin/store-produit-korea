import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Pause, Play } from 'lucide-react';
import { HeroSlideView } from './HeroSection.jsx';
import { resolveImage } from '../theme/assets.js';
import { useTheme } from '../theme/ThemeContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

const INTERVAL = 6500; // ms entre deux diapositives
const SWIPE = 40; // px minimum pour un glissement

const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

/** Diapositive de l'admin → textes de la langue affichée. Arabe vide = traduction existante du texte français. */
function localize(slide, lang, tc, media) {
  const pick = (v) => (lang === 'ar' && v?.ar ? v.ar : tc(v?.fr || ''));
  const desktop = resolveImage(slide.imageDesktop, media);
  return {
    eyebrow: pick(slide.eyebrow),
    heading: pick(slide.title),
    text: pick(slide.text),
    buttonLabel: pick(slide.buttonLabel),
    buttonLink: slide.buttonLink,
    imageAlt: pick(slide.alt),
    desktop,
    mobile: resolveImage(slide.imageMobile, media) || desktop,
  };
}

/**
 * Bannière d'accueil gérée dans Admin → Visuels marketing.
 * 1 diapositive publiée = bannière fixe (rendu identique à l'ancienne) ; plusieurs = carrousel :
 * défilement automatique, flèches, points, glissement au doigt, pause au survol / au clavier / bouton pause,
 * et aucun défilement automatique ni animation si l'appareil demande moins d'animations.
 */
export default function HeroCarousel({ slides }) {
  const { media } = useTheme();
  const { t, tc, lang, dir } = useI18n();
  const uid = useId().replace(/:/g, '');
  const count = slides.length;
  const [index, setIndex] = useState(0);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [paused, setPaused] = useState(reducedMotion); // bouton pause (activé d'office si moins d'animations)
  const touch = useRef(null);
  const rtl = dir === 'rtl';

  const go = useCallback((i) => setIndex(((i % count) + count) % count), [count]);
  const next = useCallback(() => setIndex((i) => (i + 1) % count), [count]);
  const prev = useCallback(() => setIndex((i) => (i - 1 + count) % count), [count]);

  useEffect(() => { if (index >= count) setIndex(0); }, [count, index]);

  const running = count > 1 && !paused && !hovered && !focused;
  useEffect(() => {
    if (!running) return undefined;
    const id = window.setTimeout(next, INTERVAL);
    return () => window.clearTimeout(id);
  }, [running, index, next]);

  if (count === 0) return null;
  const items = slides.map((s) => localize(s, lang, tc, media));

  if (count === 1) {
    return (
      <section className="hero" aria-labelledby={`${uid}-0`}>
        <HeroSlideView slide={items[0]} titleId={`${uid}-0`} />
      </section>
    );
  }

  const onTouchStart = (e) => { touch.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }; };
  const onTouchEnd = (e) => {
    const start = touch.current;
    touch.current = null;
    if (!start) return;
    const dx = e.changedTouches[0].clientX - start.x;
    const dy = e.changedTouches[0].clientY - start.y;
    if (Math.abs(dx) < SWIPE || Math.abs(dx) < Math.abs(dy)) return; // défilement vertical de la page
    // Glisser vers la gauche = suivante (sens inversé en arabe).
    if ((dx < 0) !== rtl) next(); else prev();
  };
  const onKeyDown = (e) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    if (e.target.closest('a, input, textarea')) return;
    e.preventDefault();
    if ((e.key === 'ArrowRight') !== rtl) next(); else prev();
  };
  const PrevIcon = rtl ? ChevronRight : ChevronLeft;
  const NextIcon = rtl ? ChevronLeft : ChevronRight;

  return (
    <section
      className="hero hero--carousel"
      aria-roledescription={t('hero.carousel')}
      aria-label={t('hero.label')}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setFocused(false); }}
      onKeyDown={onKeyDown}
    >
      <div className="hero__stage">
        <div className="hero__track" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd} aria-live={running ? 'off' : 'polite'}>
          {items.map((slide, i) => {
            const active = i === index;
            return (
              <div
                key={slides[i].id}
                id={`${uid}-slide-${i}`}
                className={`hero__slide ${active ? 'is-active' : ''}`}
                role="group"
                aria-roledescription={t('hero.slide')}
                aria-label={t('hero.slideOf', { n: i + 1, total: count })}
                aria-hidden={!active}
                inert={active ? undefined : ''}
              >
                <HeroSlideView slide={slide} titleId={`${uid}-${i}`} first={i === 0} />
              </div>
            );
          })}
        </div>

        <div className="hero__controls">
          <button type="button" className="hero__arrow" onClick={prev} aria-label={t('hero.prev')}>
            <PrevIcon size={20} aria-hidden="true" />
          </button>
          <div className="hero__dots">
            {items.map((_, i) => (
              <button
                key={slides[i].id}
                type="button"
                className={`hero__dot ${i === index ? 'is-active' : ''}`}
                aria-label={t('hero.goTo', { n: i + 1, total: count })}
                aria-current={i === index ? 'true' : undefined}
                aria-controls={`${uid}-slide-${i}`}
                onClick={() => go(i)}
              />
            ))}
          </div>
          <button type="button" className="hero__arrow" onClick={next} aria-label={t('hero.next')}>
            <NextIcon size={20} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="hero__arrow hero__pause"
            onClick={() => setPaused((p) => !p)}
            aria-label={paused ? t('hero.play') : t('hero.pause')}
            aria-pressed={paused}
          >
            {paused ? <Play size={16} aria-hidden="true" /> : <Pause size={16} aria-hidden="true" />}
          </button>
        </div>
      </div>
    </section>
  );
}
