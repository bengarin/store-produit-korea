import { useEffect, useState } from 'react';

/** Couverture de la carte ; image absente ou introuvable : motif neutre (jamais d'image cassée). */
function Cover({ cover }) {
  const [failed, setFailed] = useState(false);
  if (!cover || failed) return <span className="blog-card__placeholder"><BookOpen size={34} strokeWidth={1.2} /></span>;
  return <img src={cover.src640 || cover.src} alt="" loading="lazy" decoding="async" width="640" height="400" onError={() => setFailed(true)} />;
}
import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen } from 'lucide-react';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import { fetchArticles, localizeArticle } from '../services/contentService.js';
import { formatDate } from '../utils/date.js';

/** Liste des articles publiés (gérés dans Admin → Blog), du plus récent au plus ancien. */
export default function BlogPage() {
  const { t, lang, autoDir } = useI18n();
  const [state, setState] = useState({ status: 'loading', items: [] });

  useEffect(() => {
    const ctrl = new AbortController();
    fetchArticles({ signal: ctrl.signal })
      .then((items) => setState({ status: 'ready', items }))
      .catch(() => !ctrl.signal.aborted && setState({ status: 'error', items: [] }));
    return () => ctrl.abort();
  }, []);

  const articles = state.items.map((a) => localizeArticle(a, lang));

  return (
    <>
      <Header />
      <main className="container section blog-page">
        <header className="section-head">
          <p className="eyebrow">{t('blog.eyebrow')}</p>
          <h1 className="section-title">{t('blog.title')}</h1>
          <p className="section-intro">{t('blog.intro')}</p>
        </header>
        {state.status === 'loading' && <div className="page-loading page-loading--inline" aria-label={t('common.loading')} />}
        {state.status === 'error' && <p className="empty-inline" role="alert">{t('blog.error')}</p>}
        {state.status === 'ready' && !articles.length && (
          <div className="empty-state">
            <span className="empty-state__icon"><BookOpen size={30} strokeWidth={1.4} /></span>
            <h2>{t('blog.emptyTitle')}</h2>
            <p>{t('blog.emptyText')}</p>
          </div>
        )}
        {articles.length > 0 && (
          <ul className="blog-grid">
            {articles.map((a) => (
              <li key={a.slug} className="blog-card">
                <Link to={`/blog/${a.slug}`} className="blog-card__media" tabIndex={-1} aria-hidden="true">
                  <Cover cover={a.cover} />
                </Link>
                <div className="blog-card__body">
                  {a.publishedAt && <time className="blog-card__date" dateTime={a.publishedAt}>{formatDate(a.publishedAt, lang)}</time>}
                  <h2 className="blog-card__title" dir={autoDir}><Link to={`/blog/${a.slug}`}>{a.title}</Link></h2>
                  {a.excerpt && <p className="blog-card__excerpt" dir={autoDir}>{a.excerpt}</p>}
                  <Link to={`/blog/${a.slug}`} className="btn btn--outline blog-card__more" aria-label={t('blog.readMoreOf', { title: a.title })}>
                    {t('blog.readMore')} <ArrowRight size={16} aria-hidden="true" className="flip-rtl" />
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
