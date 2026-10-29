import { useState } from 'react';
import { Truck, HandCoins, Lock, Loader2 } from 'lucide-react';
import { STORE_CONFIG } from '../config/store.js';
import { formatPrice } from '../utils/currency.js';
import { normalizeMoroccanPhone } from '../utils/phone.js';

const EMPTY = { fullName: '', phone: '', city: '', otherCity: '', address: '' };

export function validate(values) {
  const errors = {};
  if (values.fullName.trim().length < 3) errors.fullName = 'Veuillez saisir votre nom complet.';
  if (!values.phone.trim()) errors.phone = 'Veuillez saisir votre numéro de téléphone.';
  else if (!normalizeMoroccanPhone(values.phone))
    errors.phone = 'Numéro marocain invalide (ex. 06 12 34 56 78 ou +212 6 12 34 56 78).';
  if (!values.city) errors.city = 'Veuillez choisir votre ville.';
  else if (values.city === 'autre' && values.otherCity.trim().length < 2) errors.otherCity = 'Veuillez préciser votre ville.';
  if (values.address.trim().length < 8) errors.address = 'Veuillez saisir une adresse complète (rue, numéro, quartier).';
  return errors;
}

function Field({ id, label, error, children }) {
  return (
    <div className={`field ${error ? 'has-error' : ''}`}>
      <label htmlFor={id}>
        {label} <span className="field__req" aria-hidden="true">*</span>
      </label>
      {children}
      {error && (
        <p className="field__error" id={`${id}-error`} role="alert">{error}</p>
      )}
    </div>
  );
}

export default function CheckoutForm({ deliveryFee, submitting, onSubmit, children }) {
  const [values, setValues] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  const update = (field) => (e) => {
    const next = { ...values, [field]: e.target.value };
    setValues(next);
    if (touched[field]) setErrors(validate(next));
  };
  const blur = (field) => () => {
    setTouched((t) => ({ ...t, [field]: true }));
    setErrors(validate(values));
  };
  const a11y = (field) => ({
    'aria-invalid': Boolean(errors[field] && touched[field]),
    'aria-describedby': errors[field] && touched[field] ? `${field}-error` : undefined,
  });
  const err = (field) => (touched[field] ? errors[field] : undefined);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (submitting) return;
    const found = validate(values);
    setErrors(found);
    setTouched({ fullName: true, phone: true, city: true, otherCity: true, address: true });
    if (Object.keys(found).length) {
      document.getElementById(Object.keys(found)[0])?.focus();
      return;
    }
    onSubmit({
      fullName: values.fullName.trim(),
      phone: normalizeMoroccanPhone(values.phone),
      city: values.city === 'autre' ? values.otherCity.trim() : values.city,
      address: values.address.trim(),
    });
  };

  return (
    <form className="checkout-form" onSubmit={handleSubmit} noValidate>
      <section className="checkout-section">
        <h2>Informations de livraison</h2>
        <Field id="fullName" label="Nom complet" error={err('fullName')}>
          <input id="fullName" autoComplete="name" placeholder="Votre nom complet" value={values.fullName}
            onChange={update('fullName')} onBlur={blur('fullName')} {...a11y('fullName')} />
        </Field>
        <Field id="phone" label="Téléphone" error={err('phone')}>
          <input id="phone" type="tel" inputMode="tel" autoComplete="tel" placeholder="06 XX XX XX XX" value={values.phone}
            onChange={update('phone')} onBlur={blur('phone')} {...a11y('phone')} />
        </Field>
        <Field id="city" label="Ville" error={err('city')}>
          <select id="city" value={values.city} onChange={update('city')} onBlur={blur('city')} {...a11y('city')}>
            <option value="" disabled>Choisir votre ville</option>
            {STORE_CONFIG.cities.map((c) => <option key={c} value={c}>{c}</option>)}
            <option value="autre">Autre ville…</option>
          </select>
        </Field>
        {values.city === 'autre' && (
          <Field id="otherCity" label="Votre ville" error={err('otherCity')}>
            <input id="otherCity" placeholder="Nom de votre ville" value={values.otherCity}
              onChange={update('otherCity')} onBlur={blur('otherCity')} {...a11y('otherCity')} />
          </Field>
        )}
        <Field id="address" label="Adresse complète" error={err('address')}>
          <input id="address" autoComplete="street-address" placeholder="Ex : Rue, numéro, quartier…" value={values.address}
            onChange={update('address')} onBlur={blur('address')} {...a11y('address')} />
        </Field>
      </section>

      <section className="checkout-section">
        <h2>Mode de livraison</h2>
        <div className="option-card is-selected">
          <Truck size={24} strokeWidth={1.5} />
          <div>
            <strong>Livraison à domicile</strong>
            <span>Partout au Maroc</span>
          </div>
          <span className="option-card__price">{deliveryFee === 0 ? 'Offerte' : formatPrice(deliveryFee)}</span>
        </div>
      </section>

      <section className="checkout-section">
        <h2>Mode de paiement</h2>
        <div className="option-card is-selected">
          <HandCoins size={24} strokeWidth={1.5} />
          <div>
            <strong>Paiement à la livraison (COD)</strong>
            <span>Vous payez en espèces en recevant votre commande</span>
          </div>
        </div>
      </section>

      {children}

      <div className="sticky-actions">
        <button type="submit" className="btn btn--primary btn--lg btn--block" disabled={submitting} aria-busy={submitting}>
          {submitting ? (<><Loader2 size={18} className="spin" /> Envoi en cours…</>) : 'Confirmer la commande'}
        </button>
        <p className="secure-note"><Lock size={13} /> Démo : aucune donnée n’est envoyée, tout reste dans votre navigateur.</p>
      </div>
    </form>
  );
}
