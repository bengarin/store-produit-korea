import { useEffect, useState } from 'react';
import { KeyRound, Lock, Save, Store, Truck } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import { Button, Card, ErrorState, Field, Notice, PageHeader, SkeletonRows } from '../components/ui.jsx';
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
      ['invoiceFooter', 'Pied de facture'],
    ],
    note: 'À valider avec votre comptable.',
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
      const body = Object.fromEntries(section.fields.map(([k, , , type]) => [k, type === 'number' ? Number(values[k]) : values[k]]));
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

function ShippingCard({ editable }) {
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
    <Card title={<><Truck size={17} aria-hidden="true" /> Livraison</>}>
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
      {viewStore && <ShippingCard editable={editable} />}
      <PasswordCard />
    </div>
  );
}
