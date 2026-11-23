import { Badge, Card } from '../ui.jsx';

const dateFr = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—');

/** Texte lisible d'un metafield « rich_text » / « multi_line » de Shopify (JSON) ; sinon la valeur telle quelle. */
export function readableMetafield(type, value) {
  if (!value) return '';
  if (type.includes('rich_text') || (type === 'multi_line_text_field' && value.startsWith('{"type":"root"'))) {
    try {
      const out = [];
      const walk = (node) => {
        if (node.type === 'text') out.push(node.value || '');
        (node.children || []).forEach(walk);
        if (['paragraph', 'list-item', 'heading'].includes(node.type)) out.push('\n');
      };
      walk(JSON.parse(value));
      return out.join('').replace(/\n{2,}/g, '\n').trim();
    } catch {
      return value;
    }
  }
  return value;
}

/**
 * Données recopiées de Shopify par l'import (lecture seule) : handle, type, catégorie, collections, tags et
 * metafields bruts. Elles ne se modifient pas ici : elles sont mises à jour à chaque import.
 */
export default function ShopifyDataCard({ shopify }) {
  if (!shopify) return null;
  const metafields = shopify.metafields || [];
  return (
    <Card title="Données Shopify (lecture seule)">
      <dl className="adm-shopify-data">
        <div><dt>Identifiant</dt><dd><code>{shopify.id}</code></dd></div>
        <div><dt>Handle (URL Shopify)</dt><dd><code>{shopify.handle || '—'}</code></dd></div>
        <div><dt>Type de produit</dt><dd>{shopify.productType || '—'}</dd></div>
        <div><dt>Catégorie Shopify</dt><dd>{shopify.category || '—'}</dd></div>
        <div><dt>Modifié dans Shopify</dt><dd>{dateFr(shopify.updatedAt)}</dd></div>
        <div><dt>Dernier import</dt><dd>{dateFr(shopify.syncedAt)}</dd></div>
      </dl>
      <p className="adm-shopify-data__title adm-mt">Collections Shopify</p>
      <div className="adm-chips">{shopify.collections.length ? shopify.collections.map((c) => <Badge key={c}>{c}</Badge>) : '—'}</div>
      <p className="adm-shopify-data__title adm-mt">Tags Shopify</p>
      <div className="adm-chips">{shopify.tags.length ? shopify.tags.map((t) => <Badge key={t} tone="neutral">{t}</Badge>) : '—'}</div>
      <details className="adm-mt">
        <summary>Metafields Shopify ({metafields.length})</summary>
        <div className="adm-table-wrap">
          <table className="adm-table adm-metafields">
            <thead><tr><th>Champ</th><th>Type</th><th>Valeur</th></tr></thead>
            <tbody>
              {metafields.map((m) => (
                <tr key={`${m.namespace}.${m.key}`} className={m.inShopify ? '' : 'is-muted'}>
                  <td><code>{m.namespace}.{m.key}</code>{!m.inShopify && <> <Badge tone="warning">absent de Shopify</Badge></>}</td>
                  <td><code>{m.type}</code></td>
                  <td className="adm-metafields__value">{readableMetafield(m.type, m.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <p className="adm-footnote adm-mt">Mises à jour à chaque import Shopify. Les références (metaobject, fichier) sont affichées telles quelles.</p>
    </Card>
  );
}
