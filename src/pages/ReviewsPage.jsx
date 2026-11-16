import { useEffect, useId, useState } from 'react';
import { MessageSquareHeart, Star } from 'lucide-react';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import Stars from '../components/Stars.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import { CONTENT_AVAILABLE, fetchReviews, submitReview } from '../services/contentService.js';
import { formatDate } from '../utils/date.js';

const TEXT_MIN = 10;
const TEXT_MAX = 1000;

/**
 * Avis sur la BOUTIQUE (pas sur un produit) : avis validés par l'équipe + formulaire.
 * Un avis déposé n'apparaît qu'après validation dans Admin → Avis clients.
 */
export default function ReviewsPage() {
  const { t, lang, autoDir } = useI18n();
  const [data, setData] = useState({ status: 'loading', count: 0, average: null, items: [] });

  useEffect(() => {
    const ctrl = new AbortController();
    fetchReviews({ signal: ctrl.signal })
      .then((d) => setData({ status: 'ready', ...d }))
      .catch(() => !ctrl.signal.aborted && setData((s) => ({ ...s, status: 'error' })));
    return () => ctrl.abort();
  }, []);

  return (
    <>
      <Header />
      <main className="container section reviews-page">
        <header className="section-head">
          <p className="eyebrow">{t('reviews.eyebrow')}</p>
          <h1 className="section-title">{t('reviews.title')}</h1>
          {data.count > 0 ? (
            <p className="reviews-summary">
              <Stars value={data.average} size={20} label={t('reviews.averageAria', { average: data.average })} />
              <strong>{String(data.average).replace('.', ',')}/5</strong>
              <span>· {t('reviews.count', { count: data.count })}</span>
            </p>
          ) : (
            <p className="section-intro">{t('reviews.intro')}</p>
          )}
        </header>
        <div className="reviews-layout">
          <section className="reviews-list" aria-label={t('reviews.listLabel')}>
            {data.status === 'loading' && <div className="page-loading page-loading--inline" aria-label={t('common.loading')} />}
            {data.status === 'error' && <p className="empty-inline" role="alert">{t('reviews.loadError')}</p>}
            {data.status === 'ready' && !data.items.length && (
              <div className="empty-state">
                <span className="empty-state__icon"><MessageSquareHeart size={30} strokeWidth={1.4} /></span>
                <h2>{t('reviews.emptyTitle')}</h2>
                <p>{t('reviews.emptyText')}</p>
              </div>
            )}
            {data.items.length > 0 && (
              <ul className="review-cards">
                {data.items.map((r) => (
                  <li key={r.id} className="review-card">
                    <div className="review-card__top">
                      <strong className="review-card__name" dir="auto">{r.name}</strong>
                      <time className="review-card__date" dateTime={r.date}>{formatDate(r.date, lang)}</time>
                    </div>
                    <Stars value={r.rating} label={t('reviews.ratingAria', { rating: r.rating })} />
                    <p className="review-card__text" dir={r.language === 'ar' ? 'rtl' : autoDir}>{r.text}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <ReviewForm />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}

function ReviewForm() {
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
    if (name.trim().length < 2) return setState({ status: 'error', message: t('reviews.nameRequired') });
    if (!rating) return setState({ status: 'error', message: t('reviews.ratingRequired') });
    if (text.trim().length < TEXT_MIN) return setState({ status: 'error', message: t('reviews.textTooShort', { min: TEXT_MIN }) });
    if (!consent) return setState({ status: 'error', message: t('reviews.consentRequired') });
    setState({ status: 'sending', message: '' });
    try {
      await submitReview({ name: name.trim(), rating, text: text.trim(), language: lang, consent: true, consentText: t('reviews.consent'), website });
      setState({ status: 'done', message: t('reviews.thanks') });
    } catch (err) {
      const fields = err.data?.error?.fields || err.data?.fields || {};
      const first = lang === 'fr' ? Object.values(fields).flat()[0] : null; // messages du serveur : en français
      setState({ status: 'error', message: err.status === 429 ? t('reviews.tooMany') : first || t('reviews.sendError') });
    }
  };

  if (state.status === 'done') {
    return (
      <aside className="review-form review-form--done" role="status">
        <MessageSquareHeart size={30} strokeWidth={1.4} aria-hidden="true" />
        <h2 className="review-form__title">{t('reviews.thanksTitle')}</h2>
        <p>{state.message}</p>
      </aside>
    );
  }

  const shown = hover || rating;
  return (
    <aside className="review-form" aria-labelledby={`${id}-title`}>
      <h2 className="review-form__title" id={`${id}-title`}>{t('reviews.formTitle')}</h2>
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
          <button type="submit" className="btn btn--primary btn--block" disabled={state.status === 'sending'}>
            {state.status === 'sending' ? t('reviews.sending') : t('reviews.submit')}
          </button>
          <p className="review-form__note">{t('reviews.moderationNote')}</p>
        </form>
      )}
    </aside>
  );
}
