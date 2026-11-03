import { useEffect, useState } from 'react';
import { Download, KeyRound, Lock, Mail, Save, Store, Truck } from 'lucide-react';
import { admin, adminUrl } from '../api.js';
import { useAuth } from '../auth.jsx';
import { Button, ButtonLink, Card, ErrorState, Field, Notice, PageHeader, SkeletonRows } from '../components/ui.jsx';
import AccountSecurity from '../components/AccountSecurity.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { formatMoney } from '../format.js';
import { useApi, useTitle } from '../hooks.js';
import { can } from '../permissions.js';

const SECTIONS = [
  {
    id: 'store', title: 'Boutique', icon: Store, fields: [
      ['brandName', 'Nom de la boutique'],
      ['whatsappNumber', 'Numéro WhatsApp', 'Format international, chiffres seuls (ex. 2126XXXXXXXX). Affiché aux clients.'],
      ['contactEmail', 'E-mail de contact'],
      ['contactPhone', 'Téléphone de contact'],
    ],
  },
  {
    id: 'invoice', title: 'Mentions légales des factures', icon: Lock, fields: [
      ['legalName', 'Raison sociale'],
      ['legalAddress', 'Adresse', null, 'textarea'],
      ['ice', 'ICE'],
      ['rc', 'RC'],
      ['ifNumber', 'IF'],
      ['patente', 'Taxe professionnelle (patente)'],
      ['vatRate', 'Taux de TVA (%)', 'Vide = TVA non affichée sur les factures. Les prix du site sont TTC.', 'decimal-null'],
      ['invoicePrefix', 'Préfixe des factures', 'Ex. FAC → FAC-2026-000001. Numérotation continue par année, émise à la livraison.'],
      ['invoiceFooter', 'Pied de facture'],
    ],
    note: 'Informations à fournir par vous et à valider avec votre comptable : rien n’est rempli automatiquement.',
  },
  {
    id: 'limits', title: 'Commandes en ligne', icon: Truck, fields: [
      ['maxQtyPerLine', 'Quantité maximale par produit', null, 'number'],
      ['maxOrdersPerPhonePerHour', 'Commandes maximum par téléphone et par heure', 'Protection contre les abus.', 'number'],
    ],
  },
];

function SettingsSection({ section, data, editable, onSaved }) {
  const showToast = useToast();
  const [values, setValues] = useState(() => Object.fromEntries(section.fields.map(([k]) => [k, data[k] ?? ''])));
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const dirty = section.fields.some(([k]) => String(values[k]) !== String(data[k] ?? ''));

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      const convert = (v, type) => (type === 'number' ? Number(v) : type === 'decimal-null' ? (String(v).trim() === '' ? null : String(v).replace(',', '.')) : v);
      const body = Object.fromEntries(section.fields.map(([k, , , type]) => [k, convert(values[k], type)]));
      onSaved(await admin.patch('/settings', body));
      showToast('Réglages enregistrés');
    } catch (err) {
      setErrors({ ...Object.fromEntries(Object.keys(err.fields || {}).map((k) => [k, err.fieldMessage(k)])), form: err.fields ? null : err.message });
    } finally {
      setBusy(false);
    }
  };

  const Icon = section.icon;
  return (
    <Card title={<><Icon size={17} aria-hidden="true" /> {section.title}</>}>
      <form onSubmit={save} className="adm-form-grid" noValidate>
        {section.fields.map(([key, labelText, hint, type]) => (
          <Field key={key} label={labelText} hint={hint} error={errors[key]} htmlFor={`set-${key}`}>
            {type === 'textarea' ? (
              <textarea id={`set-${key}`} className="adm-input" rows={3} value={values[key]} disabled={!editable}
                onChange={(e) => setValues((v) => ({ ...v, [key]: e.target.value }))} />
            ) : (
              <input id={`set-${key}`} className="adm-input" type={type === 'number' ? 'number' : 'text'} min={type === 'number' ? 1 : undefined}
                value={values[key]} disabled={!editable} onChange={(e) => setValues((v) => ({ ...v, [key]: e.target.value }))} />
            )}
          </Field>
        ))}
        {section.note && <p className="adm-footnote adm-form-grid__full">{section.note}</p>}
        {errors.form && <div className="adm-form-grid__full"><Notice tone="danger">{errors.form}</Notice></div>}
        {editable && (
          <div className="adm-form-grid__full">
            <Button type="submit" icon={Save} loading={busy} disabled={!dirty}>Enregistrer</Button>
          </div>
        )}
      </form>
    </Card>
  );
}

const DELIVERY_MODES = [
  ['free', 'Livraison gratuite', 'Frais de livraison : 0 DH pour toutes les commandes.'],
  ['paid', 'Livraison payante', 'Un montant unique, que vous fixez ci-dessous, pour toutes les commandes.'],
  ['zones', 'Tarifs par zone', 'Le tarif (et le seuil de gratuité) de chaque zone de livraison, plus bas.'],
];

/** Configuration de livraison : gratuite / payante (montant) / par zone. Appliquée au checkout par le serveur. */
function DeliveryConfigCard({ data, editable, onSaved }) {
  const showToast = useToast();
  const [mode, setMode] = useState(data.deliveryMode || 'zones');
  const [fee, setFee] = useState(data.deliveryFee ?? '');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const dirty = mode !== data.deliveryMode || (mode === 'paid' && String(fee) !== String(data.deliveryFee ?? ''));

  const save = async (e) => {
    e.preventDefault();
    setError(null);
    const amount = String(fee).trim().replace(',', '.');
    if (mode === 'paid' && !(Number(amount) > 0)) return setError('Indiquez le montant des frais de livraison (supérieur à 0 DH).');
    setBusy(true);
    try {
      onSaved(await admin.patch('/settings', mode === 'paid' ? { deliveryMode: mode, deliveryFee: amount } : { deliveryMode: mode }));
      showToast('Configuration de livraison enregistrée');
    } catch (err) {
      setError(err.fieldMessage?.('deliveryFee') || err.message);
    } finally {
      setBusy(false);
    }
  };

  const current = DELIVERY_MODES.find(([id]) => id === data.deliveryMode);
  return (
    <Card title={<><Truck size={17} aria-hidden="true" /> Configuration de livraison</>}>
      {!editable ? (
        <p>
          <strong>{current?.[1]}</strong>
          {data.deliveryMode === 'paid' && ` : ${formatMoney(data.deliveryFee)}`}
          {data.deliveryMode === 'free' && ' : 0 DH'}
        </p>
      ) : (
        <form onSubmit={save} className="adm-form-grid" noValidate>
          <fieldset className="adm-radio-group adm-form-grid__full">
            <legend>Mode de livraison</legend>
            {DELIVERY_MODES.map(([id, labelText, hint]) => (
              <label key={id}>
                <input type="radio" name="deliveryMode" value={id} checked={mode === id} onChange={() => setMode(id)} />{' '}
                <strong>{labelText}</strong> <span className="adm-muted">— {hint}</span>
              </label>
            ))}
          </fieldset>
          {mode === 'paid' && (
            <Field label="Montant des frais de livraison (DH)" error={error} htmlFor="set-deliveryFee">
              <input id="set-deliveryFee" className="adm-input" type="number" min="0.01" step="0.01" inputMode="decimal"
                value={fee} onChange={(e) => setFee(e.target.value)} />
            </Field>
          )}
          {mode === 'free' && <p className="adm-form-grid__full">Frais appliqués : <strong>0 DH</strong>.</p>}
          {mode !== 'paid' && error && <div className="adm-form-grid__full"><Notice tone="danger">{error}</Notice></div>}
          <p className="adm-footnote adm-form-grid__full">
            Appliqué immédiatement au panier et à la commande. Le montant est toujours recalculé par le serveur ;
            les commandes déjà passées gardent leurs frais d’origine.
          </p>
          <div className="adm-form-grid__full">
            <Button type="submit" icon={Save} loading={busy} disabled={!dirty}>Enregistrer</Button>
          </div>
        </form>
      )}
    </Card>
  );
}

function ShippingCard({ editable, mode }) {
  const showToast = useToast();
  const { data: zones, error, reload } = useApi('/shipping/zones');
  const [edit, setEdit] = useState({});
  const [busy, setBusy] = useState(null);
  if (error) return <Card title="Livraison"><ErrorState error={error} onRetry={reload} /></Card>;
  if (!zones) return <Card title="Livraison"><SkeletonRows rows={2} /></Card>;

  const save = async (zone) => {
    const e = edit[zone.id] || {};
    setBusy(zone.id);
    try {
      await admin.patch(`/shipping/zones/${zone.id}`, {
        fee: e.fee ?? zone.fee, freeOverSubtotal: (e.freeOverSubtotal ?? zone.freeOverSubtotal ?? '') === '' ? null : (e.freeOverSubtotal ?? zone.freeOverSubtotal),
      });
      setEdit((s) => ({ ...s, [zone.id]: undefined }));
      showToast('Tarif de livraison enregistré');
      reload();
    } catch (err) {
      showToast(err.message, 'info');
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card title={<><Truck size={17} aria-hidden="true" /> Zones et villes de livraison</>}>
      {mode !== 'zones' && (
        <Notice tone="info">
          Mode « {mode === 'free' ? 'Livraison gratuite' : 'Livraison payante'} » actif : les tarifs ci-dessous ne
          s’appliquent pas. Les zones servent à la liste des villes proposées aux clients.
        </Notice>
      )}
      {zones.map((z) => {
        const e = edit[z.id] || {};
        return (
          <div key={z.id} className="adm-zone">
            <div className="adm-zone__head">
              <strong>{z.name}</strong>
              <span className="adm-muted">{z.cityCount} ville{z.cityCount > 1 ? 's' : ''}{z.isDefault ? ' · accepte aussi « Autre ville »' : ''}</span>
            </div>
            {editable ? (
              <div className="adm-form-grid">
                <Field label="Frais de livraison (DH)" htmlFor={`fee-${z.id}`}>
                  <input id={`fee-${z.id}`} className="adm-input" type="number" min="0" step="0.01" value={e.fee ?? z.fee}
                    onChange={(ev) => setEdit((s) => ({ ...s, [z.id]: { ...e, fee: ev.target.value } }))} />
                </Field>
                <Field label="Livraison offerte dès (DH)" hint="Vide = jamais offerte" htmlFor={`free-${z.id}`}>
                  <input id={`free-${z.id}`} className="adm-input" type="number" min="0" step="0.01" value={e.freeOverSubtotal ?? z.freeOverSubtotal ?? ''}
                    onChange={(ev) => setEdit((s) => ({ ...s, [z.id]: { ...e, freeOverSubtotal: ev.target.value } }))} />
                </Field>
                {edit[z.id] && <div className="adm-form-grid__full"><Button size="sm" icon={Save} loading={busy === z.id} onClick={() => save(z)}>Enregistrer</Button></div>}
              </div>
            ) : (
              <p>{formatMoney(z.fee)}{z.freeOverSubtotal != null && ` · offerte dès ${formatMoney(z.freeOverSubtotal)}`}</p>
            )}
          </div>
        );
      })}
    </Card>
  );
}

function PasswordCard() {
  const showToast = useToast();
  const [form, setForm] = useState({ currentPassword: '', newPassword: '', confirm: '' });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    if (form.newPassword !== form.confirm) return setErrors({ confirm: 'Les deux mots de passe ne correspondent pas.' });
    setBusy(true);
    setErrors({});
    try {
      await admin.post('/auth/password', { currentPassword: form.currentPassword, newPassword: form.newPassword });
      setForm({ currentPassword: '', newPassword: '', confirm: '' });
      showToast('Mot de passe modifié');
    } catch (err) {
      setErrors({ currentPassword: err.fieldMessage('currentPassword'), newPassword: err.fieldMessage('newPassword'), form: err.fields ? null : err.message });
    } finally {
      setBusy(false);
    }
  };
  const input = (key, labelText, autoComplete) => (
    <Field label={labelText} error={errors[key]} htmlFor={`pw-${key}`}>
      <input id={`pw-${key}`} type="password" className="adm-input" autoComplete={autoComplete} value={form[key]}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} />
    </Field>
  );
  return (
    <Card title={<><KeyRound size={17} aria-hidden="true" /> Mon mot de passe</>}>
      <form onSubmit={submit} className="adm-form-grid" noValidate>
        {input('currentPassword', 'Mot de passe actuel', 'current-password')}
        <span className="adm-form-grid__spacer" />
        {input('newPassword', 'Nouveau mot de passe (12 caractères minimum)', 'new-password')}
        {input('confirm', 'Confirmer le nouveau mot de passe', 'new-password')}
        {errors.form && <div className="adm-form-grid__full"><Notice tone="danger">{errors.form}</Notice></div>}
        <div className="adm-form-grid__full"><Button type="submit" loading={busy} disabled={!form.currentPassword || !form.newPassword}>Changer le mot de passe</Button></div>
      </form>
    </Card>
  );
}

/** E-mails : configuration (sans secret), journal, e-mail de test — Propriétaire, Admin. */
function EmailCard() {
  const { data, error, reload } = useApi('/notifications/emails');
  const [sending, setSending] = useState(false);
  const showToast = useToast();
  const test = async () => {
    setSending(true);
    try {
      const r = await admin.post('/notifications/emails/test');
      showToast(r.status === 'skipped' ? 'E-mail non configuré : rien n’a été envoyé.' : 'E-mail de test envoyé (voir le journal).');
      reload();
    } catch (e) {
      showToast(e.message, 'info');
    } finally {
      setSending(false);
    }
  };
  return (
    <Card title={<><Mail size={17} aria-hidden="true" /> E-mails</>}
      actions={data && <Button size="sm" variant="secondary" loading={sending} onClick={test}>Envoyer un e-mail de test</Button>}>
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && !data.configured && (
        <Notice tone="warning">E-mail non configuré : aucune alerte ni confirmation n’est envoyée. Le serveur doit recevoir les paramètres SMTP de votre fournisseur (voir docs/PRODUCTION.md).</Notice>
      )}
      {data?.configured && <p>Expéditeur : <strong>{data.fromEmail}</strong> · alertes « nouvelle commande » : {data.orderNotificationRecipients} destinataire(s).</p>}
      {data?.items.length > 0 && (
        <ul className="adm-list adm-mt">
          {data.items.slice(0, 8).map((e) => (
            <li key={e.id} className="adm-list__row">
              <div><strong>{e.subject}</strong><span className="adm-muted">{e.kind} · {e.to}{e.error ? ` · ${e.error}` : ''}</span></div>
              <span className="adm-muted">{e.statusLabel}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/** Inscrits à la newsletter (section du thème) : nombre et export Excel — Propriétaire, Admin. */
function NewsletterCard() {
  const { data, error, reload } = useApi('/newsletter/subscribers');
  return (
    <Card title={<><Mail size={17} aria-hidden="true" /> Newsletter</>}
      actions={data?.total > 0 && <ButtonLink href={adminUrl('/newsletter/export')} icon={Download} download>Exporter (Excel)</ButtonLink>}>
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && (
        <p>
          <strong>{data.total} inscrit{data.total > 1 ? 's' : ''}</strong> avec consentement enregistré.{' '}
          <span className="adm-muted">Le site n’envoie aucun e-mail : importez la liste dans votre outil d’e-mailing.</span>
        </p>
      )}
    </Card>
  );
}

export default function SettingsPage() {
  useTitle('Réglages');
  const { user } = useAuth();
  const viewStore = can(user, 'viewSettings');
  const editable = can(user, 'editSettings');
  const { data, error, reload, setData } = useApi('/settings', null, { enabled: viewStore });
  const [version, setVersion] = useState(0);
  useEffect(() => setVersion((n) => n + 1), [data]);

  return (
    <div className="adm-page adm-page--narrow">
      <PageHeader title="Réglages" subtitle={viewStore && !editable ? 'Lecture seule : seuls le Propriétaire et l’Administrateur peuvent modifier ces réglages.' : null} />
      {viewStore && error && <ErrorState error={error} onRetry={reload} />}
      {viewStore && !data && !error && <SkeletonRows rows={6} />}
      {viewStore && data && SECTIONS.map((s) => (
        <SettingsSection key={`${s.id}-${version}`} section={s} data={data} editable={editable} onSaved={setData} />
      ))}
      {viewStore && data && <DeliveryConfigCard key={`delivery-${version}`} data={data} editable={editable} onSaved={setData} />}
      {viewStore && <ShippingCard editable={editable} mode={data?.deliveryMode || 'zones'} />}
      {can(user, 'viewNewsletter') && <EmailCard />}
      {can(user, 'viewNewsletter') && <NewsletterCard />}
      <AccountSecurity />
      <PasswordCard />
    </div>
  );
}
