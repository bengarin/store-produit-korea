import { useState } from 'react';
import { Link, useOutletContext, useParams } from 'react-router-dom';
import { CheckCircle2, FileText, MapPin, MessageCircle, Phone, StickyNote, User } from 'lucide-react';
import { admin, adminUrl } from '../api.js';
import { useAuth } from '../auth.jsx';
import { Badge, Button, ButtonLink, Card, ErrorState, Field, Modal, Notice, PageHeader, PaymentBadge, SkeletonRows, StatusBadge } from '../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { ORDER_STATUS, STATUS_ACTION, formatDate, formatMoney, formatPhone, whatsappLink } from '../format.js';
import { useApi, useTitle } from '../hooks.js';
import { can } from '../permissions.js';

const DANGER = new Set(['cancelled', 'returned']);

function StatusDialog({ order, target, onClose, onDone }) {
  const [note, setNote] = useState('');
  const [restock, setRestock] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      const updated = await admin.post(`/orders/${order.id}/status`, { status: target, note, restock });
      onDone(updated);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };
  return (
    <Modal open title={STATUS_ACTION[target]} onClose={onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Retour</Button>
          <Button variant={DANGER.has(target) ? 'danger' : 'primary'} loading={busy} onClick={submit}>Confirmer</Button>
        </>
      )}>
      <p>
        Commande <strong>{order.number}</strong> : <StatusBadge status={order.status} /> → <StatusBadge status={target} />
      </p>
      {target === 'cancelled' && <Notice tone="info">Les articles seront remis en stock et le code promo éventuel sera libéré.</Notice>}
      {target === 'delivered' && <Notice tone="info">La commande sera marquée comme payée (paiement encaissé à la livraison).</Notice>}
      {target === 'returned' && (
        <label className="adm-check">
          <input type="checkbox" checked={restock} onChange={(e) => setRestock(e.target.checked)} />
          Remettre les articles en stock (décochez si les produits sont abîmés)
        </label>
      )}
      <Field label="Note (facultative, visible dans l’historique)" htmlFor="status-note">
        <textarea id="status-note" className="adm-input" rows={3} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
      </Field>
      {error && <Notice tone="danger">{error}</Notice>}
    </Modal>
  );
}

export default function OrderDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const showToast = useToast();
  const outlet = useOutletContext();
  const { data: order, error, reload, setData } = useApi(`/orders/${id}`);
  const [target, setTarget] = useState(null);
  const [note, setNote] = useState(null);
  const [savingNote, setSavingNote] = useState(false);
  useTitle(order ? `Commande ${order.number}` : 'Commande');
  const manage = can(user, 'manageOrders');

  if (error) return <div className="adm-page"><PageHeader title="Commande" back={{ to: '/admin/orders', label: 'Commandes' }} /><ErrorState error={error} onRetry={reload} /></div>;
  if (!order) return <div className="adm-page"><SkeletonRows rows={8} /></div>;

  const wa = whatsappLink(order.phone, `Bonjour ${order.customerName}, nous vous contactons au sujet de votre commande ${order.number} sur Ma Petite Corée.`);
  const noteValue = note ?? order.internalNote;

  const saveNote = async () => {
    setSavingNote(true);
    try {
      setData(await admin.patch(`/orders/${order.id}`, { internalNote: noteValue }));
      setNote(null);
      showToast('Note enregistrée');
    } catch (err) {
      showToast(err.message, 'info');
    } finally {
      setSavingNote(false);
    }
  };

  return (
    <div className="adm-page">
      <PageHeader
        back={{ to: '/admin/orders', label: 'Commandes' }}
        title={order.number}
        badge={<><StatusBadge status={order.status} /> <PaymentBadge status={order.paymentStatus} /></>}
        subtitle={`Passée le ${formatDate(order.placedAt)} · ${order.itemCount} article${order.itemCount > 1 ? 's' : ''}`}
        actions={(
          <>
            <ButtonLink href={adminUrl(`/orders/${order.id}/invoice`)} target="_blank" rel="noopener noreferrer" icon={FileText}>Facture</ButtonLink>
            {wa && <ButtonLink href={wa} target="_blank" rel="noopener noreferrer" icon={MessageCircle}>WhatsApp</ButtonLink>}
          </>
        )}
      />

      {manage && order.allowedTransitions.length > 0 && (
        <div className="adm-actions-bar" aria-label="Changer le statut">
          {order.allowedTransitions
            .slice()
            .sort((a, b) => Number(DANGER.has(a)) - Number(DANGER.has(b)))
            .map((s) => (
              <Button key={s} variant={DANGER.has(s) ? 'danger-ghost' : 'primary'} icon={DANGER.has(s) ? undefined : CheckCircle2}
                onClick={() => setTarget(s)}>{STATUS_ACTION[s]}</Button>
            ))}
        </div>
      )}

      <div className="adm-detail">
        <div className="adm-detail__main">
          <Card title="Articles" padded={false}>
            <div className="adm-table-wrap">
              <table className="adm-table adm-table--stack">
                <thead><tr><th>Produit</th><th>SKU</th><th className="num">Prix</th><th className="num">Qté</th><th className="num">Total</th>{order.items[0]?.unitCost !== undefined && <th className="num">Coût</th>}</tr></thead>
                <tbody>
                  {order.items.map((it) => (
                    <tr key={it.id}>
                      <td data-label="Produit"><span className="adm-cell-main">{it.productName}</span>{it.variantTitle && it.variantTitle !== 'Par défaut' && <span className="adm-muted adm-cell-sub">{it.variantTitle}</span>}</td>
                      <td data-label="SKU">{it.sku || '—'}</td>
                      <td data-label="Prix" className="num">{formatMoney(it.unitPrice)}</td>
                      <td data-label="Qté" className="num">{it.quantity}</td>
                      <td data-label="Total" className="num adm-num">{formatMoney(it.lineTotal)}</td>
                      {it.unitCost !== undefined && <td data-label="Coût" className="num adm-muted">{it.unitCost == null ? '—' : formatMoney(it.unitCost)}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <dl className="adm-totals">
              <div><dt>Sous-total</dt><dd>{formatMoney(order.subtotal)}</dd></div>
              {Number(order.discount) > 0 && <div><dt>Remise {order.couponCode && <Badge>{order.couponCode}</Badge>}</dt><dd>− {formatMoney(order.discount)}</dd></div>}
              <div><dt>Livraison {order.shippingZone && <span className="adm-muted">({order.shippingZone})</span>}</dt><dd>{Number(order.shippingFee) === 0 ? 'Offerte' : formatMoney(order.shippingFee)}</dd></div>
              <div className="adm-totals__grand"><dt>Total</dt><dd>{formatMoney(order.total)}</dd></div>
            </dl>
          </Card>

          <Card title="Historique">
            <ol className="adm-timeline">
              {order.history.slice().reverse().map((h, i) => (
                <li key={`${h.createdAt}-${i}`}>
                  <span className={`adm-timeline__dot adm-timeline__dot--${ORDER_STATUS[h.toStatus]?.tone || 'neutral'}`} aria-hidden="true" />
                  <div>
                    <strong>{ORDER_STATUS[h.toStatus]?.label || h.toStatus}</strong>
                    <span className="adm-muted"> · {formatDate(h.createdAt)} · {h.changedBy || 'Client (boutique en ligne)'}</span>
                    {h.note && <p className="adm-timeline__note">{h.note}</p>}
                  </div>
                </li>
              ))}
            </ol>
          </Card>
        </div>

        <aside className="adm-detail__side">
          <Card title="Client">
            <p className="adm-line"><User size={16} aria-hidden="true" /> <Link to={`/admin/customers/${order.customerId}`} className="adm-strong-link">{order.customerName}</Link></p>
            <p className="adm-line"><Phone size={16} aria-hidden="true" /> <a href={`tel:${order.phone}`}>{formatPhone(order.phone)}</a></p>
            {wa && <p className="adm-line"><MessageCircle size={16} aria-hidden="true" /> <a href={wa} target="_blank" rel="noopener noreferrer">Écrire sur WhatsApp</a></p>}
          </Card>
          <Card title="Livraison">
            <p className="adm-line"><MapPin size={16} aria-hidden="true" /> <span>{order.address}<br />{order.city}</span></p>
            <p className="adm-muted">Livraison à domicile · Paiement à la livraison (COD)</p>
          </Card>
          {order.customerNote && <Card title="Message du client"><p>{order.customerNote}</p></Card>}
          <Card title="Note interne">
            <textarea className="adm-input" rows={4} value={noteValue} disabled={!manage} aria-label="Note interne"
              placeholder={manage ? 'Visible uniquement par l’équipe' : 'Aucune note'} onChange={(e) => setNote(e.target.value)} />
            {manage && note !== null && note !== order.internalNote && (
              <Button size="sm" icon={StickyNote} loading={savingNote} onClick={saveNote} className="adm-mt">Enregistrer la note</Button>
            )}
          </Card>
        </aside>
      </div>

      {target && (
        <StatusDialog order={order} target={target} onClose={() => setTarget(null)}
          onDone={(updated) => {
            setTarget(null);
            setData(updated);
            outlet?.refreshPending?.();
            showToast(`Commande ${ORDER_STATUS[updated.status].label.toLowerCase()}`);
          }} />
      )}
    </div>
  );
}
