import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ImagePlus, Save, Send, Trash2, X } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import RichTextEditor from '../components/RichTextEditor.jsx';
import MediaPicker from '../components/theme/MediaPicker.jsx';
import { Badge, Button, Card, ErrorState, Field, Notice, PageHeader, PageLoader } from '../components/ui.jsx';
import { useApi, useTitle } from '../hooks.js';
import { can } from '../permissions.js';
import { ARTICLE_STATUS } from './BlogPage.jsx';

const EMPTY = {
  title: '', titleAr: '', slug: '', excerpt: '', excerptAr: '', bodyHtml: '', bodyHtmlAr: '',
  coverId: null, cover: null, coverAlt: '', status: 'draft', publishedAt: null,
};

/** ISO → valeur d'un champ « date et heure » (heure locale) et inversement. */
const toLocalInput = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const fromLocalInput = (value) => (value ? new Date(value).toISOString() : null);

/** Admin → Blog → nouvel article / modifier : textes FR et AR, couverture, statut et date de publication. */
export default function BlogEditPage() {
  const { id } = useParams();
  const isNew = id === 'new';
  useTitle(isNew ? 'Nouvel article' : 'Modifier l’article');
  const { user } = useAuth();
  const editable = can(user, 'editBlog');
  const navigate = useNavigate();
  const { data, error, reload } = useApi(isNew ? null : `/blog/articles/${id}`);
  const [form, setForm] = useState(isNew ? EMPTY : null);
  const [version, setVersion] = useState(0);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState('');
  const [picking, setPicking] = useState(false);

  useEffect(() => {
    if (data) {
      setForm({ ...EMPTY, ...data });
      setVersion((v) => v + 1);
    }
  }, [data]);

  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!form) return <PageLoader />;

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e?.target ? e.target.value : e }));

  const save = async (status) => {
    setBusy(status);
    setErrors({});
    setMessage(null);
    const body = {
      title: form.title, titleAr: form.titleAr, slug: form.slug, excerpt: form.excerpt, excerptAr: form.excerptAr,
      bodyHtml: form.bodyHtml, bodyHtmlAr: form.bodyHtmlAr, coverId: form.coverId, coverAlt: form.coverAlt,
      status, publishedAt: form.publishedAt,
    };
    try {
      const saved = isNew ? await admin.post('/blog/articles', body) : await admin.patch(`/blog/articles/${id}`, body);
      setForm({ ...EMPTY, ...saved });
      setVersion((v) => v + 1);
      setMessage({ tone: 'success', text: status === 'published' ? 'Article publié : il est visible sur la page Blog.' : 'Brouillon enregistré (non visible dans la boutique).' });
      if (isNew) navigate(`/admin/blog/${saved.id}`, { replace: true });
    } catch (err) {
      setErrors(err.fields || {});
      setMessage({ tone: 'danger', text: err.message });
    } finally {
      setBusy('');
    }
  };

  const err = (key) => errors[key]?.[0];
  const published = form.status === 'published';
  const scheduled = published && form.publishedAt && new Date(form.publishedAt) > new Date();

  return (
    <div className="adm-page">
      <PageHeader title={isNew ? 'Nouvel article' : form.title || 'Article'} back={{ to: '/admin/blog', label: 'Blog' }}
        badge={!isNew && <Badge tone={ARTICLE_STATUS[form.status].tone}>{scheduled ? 'Programmé' : ARTICLE_STATUS[form.status].label}</Badge>}
        actions={editable && (
          <>
            <Button variant="secondary" icon={Save} loading={busy === 'draft'} disabled={Boolean(busy)} onClick={() => save('draft')}>
              {published ? 'Repasser en brouillon' : 'Enregistrer le brouillon'}
            </Button>
            <Button icon={Send} loading={busy === 'published'} disabled={Boolean(busy)} onClick={() => save('published')}>
              {published ? 'Enregistrer' : 'Publier'}
            </Button>
          </>
        )} />
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      {scheduled && <Notice tone="info">Publication programmée : l’article apparaîtra automatiquement à la date choisie.</Notice>}
      <div className="adm-blog-edit">
        <div className="adm-blog-edit__main">
          <Card title="Français">
            <Field label="Titre" htmlFor="be-title" required error={err('title')}>
              <input id="be-title" className="adm-input" value={form.title} onChange={set('title')} maxLength={200} disabled={!editable} />
            </Field>
            <Field label="Résumé" htmlFor="be-excerpt" hint="Affiché sur la carte de l’article et dans Google (300 caractères max.)." error={err('excerpt')}>
              <textarea id="be-excerpt" className="adm-input" rows={3} value={form.excerpt} onChange={set('excerpt')} maxLength={300} disabled={!editable} />
            </Field>
            <Field label="Texte" htmlFor="be-body" required={published} error={err('bodyHtml')}>
              <RichTextEditor id="be-body" value={form.bodyHtml} resetKey={`fr-${version}`} onChange={set('bodyHtml')} disabled={!editable}
                placeholder="Rédigez le texte de l’article…" />
            </Field>
          </Card>
          <Card title="Arabe (facultatif)">
            <p className="adm-muted">Laissé vide : le texte français est affiché aux visiteurs qui ont choisi l’arabe.</p>
            <div dir="rtl" lang="ar">
              <Field label="العنوان" htmlFor="be-title-ar" error={err('titleAr')}>
                <input id="be-title-ar" className="adm-input" value={form.titleAr} onChange={set('titleAr')} maxLength={200} disabled={!editable} />
              </Field>
              <Field label="الملخص" htmlFor="be-excerpt-ar" error={err('excerptAr')}>
                <textarea id="be-excerpt-ar" className="adm-input" rows={3} value={form.excerptAr} onChange={set('excerptAr')} maxLength={300} disabled={!editable} />
              </Field>
              <Field label="النص" htmlFor="be-body-ar" error={err('bodyHtmlAr')}>
                <RichTextEditor id="be-body-ar" value={form.bodyHtmlAr} resetKey={`ar-${version}`} onChange={set('bodyHtmlAr')} disabled={!editable}
                  placeholder="اكتبوا نص المقال…" />
              </Field>
            </div>
          </Card>
        </div>
        <div className="adm-blog-edit__side">
          <Card title="Image de couverture">
            {form.cover ? (
              <figure className="adm-blog-cover">
                <img src={form.cover.src640 || form.cover.src} alt={form.coverAlt || ''} />
                {editable && (
                  <Button variant="ghost" size="sm" icon={X} onClick={() => setForm((f) => ({ ...f, coverId: null, cover: null }))}>Retirer</Button>
                )}
              </figure>
            ) : (
              <p className="adm-muted">Aucune image : un motif neutre est affiché.</p>
            )}
            {editable && (
              <div className="adm-blog-cover__pick">
                <Button variant="secondary" icon={ImagePlus} onClick={() => setPicking(true)}>{form.cover ? 'Changer l’image' : 'Choisir une image'}</Button>
              </div>
            )}
            <Field label="Texte alternatif" htmlFor="be-cover-alt" hint="Décrit l’image (accessibilité, Google)." error={err('coverAlt')}>
              <input id="be-cover-alt" className="adm-input" value={form.coverAlt} onChange={set('coverAlt')} maxLength={255} disabled={!editable} />
            </Field>
          </Card>
          <Card title="Publication">
            <Field label="Date de publication" htmlFor="be-date" hint="Vide : date du jour à la publication. Date future : publication programmée." error={err('publishedAt')}>
              <input id="be-date" type="datetime-local" className="adm-input" value={toLocalInput(form.publishedAt)}
                onChange={(e) => setForm((f) => ({ ...f, publishedAt: fromLocalInput(e.target.value) }))} disabled={!editable} />
            </Field>
            <Field label="Adresse de la page" htmlFor="be-slug" hint={`/blog/${form.slug || 'générée-depuis-le-titre'}`} error={err('slug')}>
              <input id="be-slug" className="adm-input" value={form.slug} onChange={set('slug')} maxLength={120} disabled={!editable}
                pattern="[a-z0-9-]*" placeholder="générée automatiquement" />
            </Field>
          </Card>
          {!isNew && can(user, 'deleteBlog') && (
            <p className="adm-muted"><Trash2 size={14} aria-hidden="true" /> Supprimer : depuis la liste des articles.</p>
          )}
        </div>
      </div>
      {picking && (
        <MediaPicker canUpload={editable} onClose={() => setPicking(false)}
          onPick={(m) => {
            setForm((f) => ({ ...f, coverId: m.id, cover: { src: m.url, src640: m.url640, alt: m.alt }, coverAlt: f.coverAlt || m.alt || '' }));
            setPicking(false);
          }} />
      )}
    </div>
  );
}
