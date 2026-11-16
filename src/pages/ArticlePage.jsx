import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import { fetchArticle, localizeArticle } from '../services/contentService.js';
import { formatDate } from '../utils/date.js';
import { sanitizeRichText } from '../utils/richText.js';

/** Article du blog : titre, date, couverture et texte (HTML limité, nettoyé par le serveur puis ici). */
export default function ArticlePage() {
  const { slug } = useParams();
  const { t, lang, autoDir } = useI18n();
  const [state, setState] = useState({ status: 'loading', article: null });

  useEffect(() => {
    const ctrl = new AbortController();
    setState({ status: 'loading', article: null });
    fetchArticle(slug, { signal: ctrl.signal })
      .then((article) => setState({ status: article ? 'ready' : 'missing', article }))
      .catch((err) => !ctrl.signal.aborted && setState({ status: err.status === 404 ? 'missing' : 'error', article: null }));
    return () => ctrl.abort();
  }, [slug]);

  const a = state.article && localizeArticle(state.article, lang);

  return (
    <>
      <Header />
      <main className="container section article-page">
        <Link to="/blog" className="article-page__back"><ArrowLeft size={17} aria-hidden="true" className="flip-rtl" /> {t('blog.back')}</Link>
        {state.status === 'loading' && <div className="page-loading page-loading--inline" aria-label={t('common.loading')} />}
        {state.status === 'missing' && (
          <div className="empty-state">
            <h1>{t('blog.notFound')}</h1>
            <Link className="btn btn--primary" to="/blog">{t('blog.back')}</Link>
          </div>
        )}
        {state.status === 'error' && <p className="empty-inline" role="alert">{t('blog.error')}</p>}
        {a && (
          <article className="article">
            <header className="article__head">
              {a.publishedAt && <time className="article__date" dateTime={a.publishedAt}>{formatDate(a.publishedAt, lang)}</time>}
              <h1 className="article__title" dir={autoDir}>{a.title}</h1>
              {a.excerpt && <p className="article__excerpt" dir={autoDir}>{a.excerpt}</p>}
            </header>
            {a.cover && (
              <img className="article__cover" src={a.cover.src} srcSet={a.cover.src640 ? `${a.cover.src640} 640w, ${a.cover.src} 1200w` : undefined}
                sizes="(min-width: 800px) 760px, 92vw" alt={a.cover.alt || ''} width="1200" height="750" />
            )}
            <div className="article__body pdp-desc__rich" dir={autoDir} dangerouslySetInnerHTML={{ __html: sanitizeRichText(a.bodyHtml || '') }} />
            <footer className="article__foot">
              <Link to="/blog" className="btn btn--outline">{t('blog.back')}</Link>
              <Link to="/produits" className="btn btn--primary">{t('blog.shop')}</Link>
            </footer>
          </article>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
