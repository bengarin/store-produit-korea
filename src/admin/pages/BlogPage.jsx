import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BookOpen, Eye, EyeOff, Pencil, Plus, Trash2 } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import SearchBox from '../components/SearchBox.jsx';
import { Badge, Button, ButtonLink, Card, EmptyState, ErrorState, Notice, PageHeader, Pagination, SkeletonRows } from '../components/ui.jsx';
import { formatDate } from '../format.js';
import { useApi, useTitle, useUrlFilters } from '../hooks.js';
import { can } from '../permissions.js';

export const ARTICLE_STATUS = { draft: { label: 'Brouillon', tone: 'neutral' }, published: { label: 'Publié', tone: 'success' } };
const FILTERS = [['', 'Tous'], ['published', 'Publiés'], ['draft', 'Brouillons']];

/** Admin → Blog : liste des articles, publier / dépublier, supprimer. */
export default function BlogPage() {
  useTitle('Blog');
  const { user } = useAuth();
  const editable = can(user, 'editBlog');
  const navigate = useNavigate();
  const [filters, setFilters] = useUrlFilters({ status: '', search: '', page: '1' });
  const { data, error, loading, reload } = useApi('/blog/articles', {
    status: filters.status || undefined, search: filters.search || undefined, page: filters.page, page_size: 20,
  });
  const [removing, setRemoving] = useState(null);
  const [message, setMessage] = useState(null);

  const togglePublish = async (a) => {
    setMessage(null);
    try {
      await admin.patch(`/blog/articles/${a.id}`, { status: a.status === 'published' ? 'draft' : 'published' });
      setMessage({ tone: 'success', text: a.status === 'published' ? `« ${a.title} » est repassé en brouillon.` : `« ${a.title} » est publié.` });
      reload();
    } catch (err) {
      setMessage({ tone: 'danger', text: err.fieldMessage?.('bodyHtml') || err.message });
    }
  };

  return (
    <div className="adm-page">
      <PageHeader title="Blog" subtitle="Articles affichés sur la page « Blog » de la boutique (français et arabe)."
        actions={editable && <ButtonLink variant="primary" icon={Plus} to="/admin/blog/new">Nouvel article</ButtonLink>} />
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      <div className="adm-filters">
        <div className="adm-chips" role="group" aria-label="Statut">
          {FILTERS.map(([value, label]) => (
            <button key={value} type="button" className={`adm-chip ${filters.status === value ? 'is-active' : ''}`}
              aria-pressed={filters.status === value} onClick={() => setFilters({ status: value })}>{label}</button>
          ))}
        </div>
        <SearchBox value={filters.search} onChange={(search) => setFilters({ search })} placeholder="Rechercher un article" />
      </div>
      <Card padded={false}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {!data && !error && <SkeletonRows />}
        {data && data.items.length === 0 && (
          <EmptyState icon={BookOpen} title="Aucun article" text={filters.status || filters.search ? 'Aucun article ne correspond à ces filtres.' : 'Écrivez votre premier article de blog.'}
            action={editable && !filters.status && !filters.search && <ButtonLink variant="primary" icon={Plus} to="/admin/blog/new">Nouvel article</ButtonLink>} />
        )}
        {data && data.items.length > 0 && (
          <ul className={`adm-articles ${loading ? 'is-loading' : ''}`}>
            {data.items.map((a) => (
              <li key={a.id} className="adm-article">
                <span className="adm-article__thumb">{a.cover ? <img src={a.cover.src640 || a.cover.src} alt="" /> : <BookOpen size={20} aria-hidden="true" />}</span>
                <span className="adm-article__main">
                  <Link to={`/admin/blog/${a.id}`} className="adm-article__title">{a.title}</Link>
                  <span className="adm-muted">
                    {a.status === 'published' && a.publishedAt ? `Publié le ${formatDate(a.publishedAt, { time: false })}` : `Modifié le ${formatDate(a.updatedAt)}`}
                    {a.titleAr ? '' : ' · titre arabe à saisir'}
                  </span>
                </span>
                <Badge tone={ARTICLE_STATUS[a.status].tone}>{ARTICLE_STATUS[a.status].label}</Badge>
                <span className="adm-article__actions">
                  {a.status === 'published' && (
                    <ButtonLink variant="ghost" icon={Eye} to={`/blog/${a.slug}`} target="_blank" rel="noopener">Voir</ButtonLink>
                  )}
                  {editable && (
                    <>
                      <Button variant="ghost" size="sm" icon={Pencil} onClick={() => navigate(`/admin/blog/${a.id}`)}>Modifier</Button>
                      <Button variant="ghost" size="sm" icon={a.status === 'published' ? EyeOff : Eye} onClick={() => togglePublish(a)}>
                        {a.status === 'published' ? 'Dépublier' : 'Publier'}
                      </Button>
                    </>
                  )}
                  {can(user, 'deleteBlog') && (
                    <Button variant="ghost" size="sm" icon={Trash2} aria-label={`Supprimer « ${a.title} »`} onClick={() => setRemoving(a)}>Supprimer</Button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      {data && <Pagination page={Number(filters.page)} pageSize={data.pageSize} total={data.total} onChange={(page) => setFilters({ page: String(page) }, { resetPage: false })} />}
      {removing && (
        <ConfirmDialog title="Supprimer l'article ?" danger confirmLabel="Supprimer" onClose={() => setRemoving(null)}
          onConfirm={async () => {
            await admin.del(`/blog/articles/${removing.id}`);
            setMessage({ tone: 'success', text: `« ${removing.title} » a été supprimé.` });
            setRemoving(null);
            reload();
          }}>
          <p>« {removing.title} » sera supprimé définitivement. L’image de couverture reste dans la médiathèque.</p>
        </ConfirmDialog>
      )}
    </div>
  );
}
