import { useId, useState } from 'react';
import { BadgeCheck, MessageSquareHeart, PenLine, Star } from 'lucide-react';
import Stars from './Stars.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import { CONTENT_AVAILABLE, submitProductReview } from '../services/contentService.js';
import { formatDate } from '../utils/date.js';

const TEXT_MIN = 10;
const TEXT_MAX = 1000;

/** Résumé près du titre : « ★★★★☆ 4,5 · 12 avis » → lien vers la section des avis. */
export function ReviewSummary({ reviews }) {
  const { t } = useI18n();
  if (!reviews || reviews.count === 0) return null;
  return (
    <a href="#avis" className="pdp-rating" onClick={(e) => {
      e.preventDefault();
      document.getElementById('avis')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }}>
      <Stars value={reviews.average} size={16} label={t('reviews.averageAria', { average: reviews.average })} />
      <strong>{String(reviews.average).replace('.', ',')}</strong>
      <span>{t('reviews.count', { count: reviews.count })}</span>
    </a>
  );
}

/**
 * Avis sur CE produit (séparés des avis sur la boutique /avis et des témoignages de l'accueil) :
 * moyenne, avis approuvés, badge « Achat vérifié » (fourni par le serveur) et formulaire « Laisser un avis ».
 */
export default function ProductReviews({ product, reviews }) {
  const { t, lang, autoDir } = useI18n();
  const [writing, setWriting] = useState(false);
  return (
    <section className="pdp-reviews" id="avis" aria-labelledby="pdp-reviews-title">
      <div className="container">
        <header className="pdp-reviews__head">
          <div>
            <h2 className="pdp-reviews__title" id="pdp-reviews-title">{t('pr.title')}</h2>
            {reviews.count > 0 ? (
              <p className="reviews-summary">
                <Stars value={reviews.average} size={20} label={t('reviews.averageAria', { average: reviews.average })} />
                <strong>{String(reviews.average).replace('.', ',')}/5</strong>
                <span>· {t('reviews.count', { count: reviews.count })}</span>
              </p>
            ) : (
              reviews.status !== 'loading' && <p className="pdp-reviews__empty">{t('pr.empty')}</p>
            )}
          </div>
          {!writing && (
            <button type="button" className="btn btn--outline" onClick={() => setWriting(true)} aria-expanded={writing}>
              <PenLine size={17} aria-hidden="true" /> {t('pr.write')}
            </button>
          )}
        </header>
        <div className={`pdp-reviews__body ${writing ? 'is-writing' : ''}`}>
          {reviews.items.length > 0 && (
            <ul className="review-cards">
              {reviews.items.map((r) => (
                <li key={r.id} className="review-card">
                  <div className="review-card__top">
                    <strong className="review-card__name" dir="auto">{r.name}</strong>
                    <time className="review-card__date" dateTime={r.date}>{formatDate(r.date, lang)}</time>
                  </div>
                  <div className="review-card__meta">
                    <Stars value={r.rating} label={t('reviews.ratingAria', { rating: r.rating })} />
                    {r.verifiedPurchase && (
                      <span className="verified-badge"><BadgeCheck size={15} aria-hidden="true" /> {t('pr.verified')}</span>
                    )}
                  </div>
                  <p className="review-card__text" dir={r.language === 'ar' ? 'rtl' : autoDir}>{r.text}</p>
                </li>
              ))}
            </ul>
          )}
          {writing && <ProductReviewForm product={product} onCancel={() => setWriting(false)} />}
        </div>
      </div>
    </section>
  );
}

function ProductReviewForm({ product, onCancel }) {
  const { t, lang } = useI18n();
  const id = useId();
  const [name, setName] = useState('');
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [text, setText] = useState('');
  const [consent, setConsent] = useState(false);
  const [website, setWebsite] = useState(''); // champ piège (invisible)
  const [state, setState] = useState({ status: 'idle', message: '' });

  const submit = async (e) => {
    e.preventDefault();
    if (!rating) return setState({ status: 'error', message: t('reviews.ratingRequired') });
    if (name.trim().length < 2) return setState({ status: 'error', message: t('reviews.nameRequired') });
    if (text.trim().length < TEXT_MIN) return setState({ status: 'error', message: t('reviews.textTooShort', { min: TEXT_MIN }) });
    if (!consent) return setState({ status: 'error', message: t('reviews.consentRequired') });
    setState({ status: 'sending', message: '' });
    try {
      await submitProductReview(product.slug, {
        name: name.trim(), rating, text: text.trim(), language: lang, consent: true, consentText: t('reviews.consent'), website,
      });
      setState({ status: 'done', message: t('pr.thanks') });
    } catch (err) {
      const fields = err.data?.error?.fields || {};
      const first = lang === 'fr' ? Object.values(fields).flat()[0] : null; // messages du serveur : en français
      setState({ status: 'error', message: err.status === 429 ? t('reviews.tooMany') : first || t('reviews.sendError') });
    }
  };

  if (state.status === 'done') {
    return (
      <div className="review-form review-form--done" role="status">
        <MessageSquareHeart size={30} strokeWidth={1.4} aria-hidden="true" />
        <h3 className="review-form__title">{t('reviews.thanksTitle')}</h3>
        <p>{state.message}</p>
      </div>
    );
  }

  const shown = hover || rating;
  return (
    <div className="review-form" aria-labelledby={`${id}-title`}>
      <h3 className="review-form__title" id={`${id}-title`}>{t('pr.write')}</h3>
      <p className="review-form__product" dir="auto">{product.displayName}</p>
      {!CONTENT_AVAILABLE ? (
        <p className="review-form__note">{t('reviews.demo')}</p>
      ) : (
        <form onSubmit={submit} noValidate>
          <fieldset className="rating-input" onMouseLeave={() => setHover(0)}>
            <legend>{t('reviews.ratingLabel')}</legend>
            <div className="rating-input__stars">
              {[1, 2, 3, 4, 5].map((n) => (
                <label key={n} className={`rating-input__star ${shown >= n ? 'is-on' : ''}`} onMouseEnter={() => setHover(n)}>
                  <input type="radio" name={`${id}-rating`} value={n} checked={rating === n} onChange={() => setRating(n)} className="sr-only" />
                  <Star size={30} strokeWidth={1.4} aria-hidden="true" />
                  <span className="sr-only">{t('reviews.ratingAria', { rating: n })}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="field">
            <label htmlFor={`${id}-name`}>{t('reviews.nameLabel')}</label>
            <input id={`${id}-name`} value={name} onChange={(e) => setName(e.target.value)} maxLength={60} autoComplete="given-name" />
            <small className="field__hint">{t('reviews.nameHint')}</small>
          </div>
          <div className="field">
            <label htmlFor={`${id}-text`}>{t('reviews.textLabel')}</label>
            <textarea id={`${id}-text`} value={text} onChange={(e) => setText(e.target.value)} rows={5} maxLength={TEXT_MAX} dir="auto" />
            <small className="field__hint">{text.length}/{TEXT_MAX}</small>
          </div>
          <div className="sr-only" aria-hidden="true">
            <label htmlFor={`${id}-website`}>Website</label>
            <input id={`${id}-website`} tabIndex={-1} autoComplete="off" value={website} onChange={(e) => setWebsite(e.target.value)} />
          </div>
          <label className="review-form__consent">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>{t('reviews.consent')}</span>
          </label>
          {state.status === 'error' && <p className="field__error" role="alert">{state.message}</p>}
          <div className="review-form__actions">
            <button type="button" className="btn btn--outline" onClick={onCancel}>{t('pr.cancel')}</button>
            <button type="submit" className="btn btn--primary" disabled={state.status === 'sending'}>
              {state.status === 'sending' ? t('reviews.sending') : t('reviews.submit')}
            </button>
          </div>
          <p className="review-form__note">{t('reviews.moderationNote')}</p>
        </form>
      )}
    </div>
  );
}
