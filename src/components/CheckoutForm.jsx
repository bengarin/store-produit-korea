import { useMemo, useState } from 'react';
import { Truck, HandCoins, Lock, Loader2 } from 'lucide-react';
import { useCatalog } from '../context/CatalogContext.jsx';
import { ORDERS_ARE_SIMULATED } from '../services/orderService.js';
import { formatPrice } from '../utils/currency.js';
import { normalizeMoroccanPhone } from '../utils/phone.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { FREE_CITY, OTHER_CITY, cityOptions, searchKey } from '../data/moroccoCities.js';

const EMPTY = { fullName: '', phone: '', city: '', otherCity: '', address: '' };

/** Erreurs du formulaire : codes de message (traduits à l'affichage). */
export function validate(values) {
  const errors = {};
  if (values.fullName.trim().length < 3) errors.fullName = 'form.errName';
  if (!values.phone.trim()) errors.phone = 'form.errPhoneEmpty';
  else if (!normalizeMoroccanPhone(values.phone)) errors.phone = 'form.errPhone';
  if (!values.city) errors.city = 'form.errCity';
  else if (values.city === OTHER_CITY && !FREE_CITY.test(values.otherCity.trim())) errors.otherCity = 'form.errOtherCity';
  if (values.address.trim().length < 8) errors.address = 'form.errAddress';
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

export default function CheckoutForm({ deliveryFee, submitting, onSubmit, alert = null, children }) {
  const { config } = useCatalog();
  const { t, lang } = useI18n();
  const [citySearch, setCitySearch] = useState('');
  const cities = useMemo(() => cityOptions(config.cities || [], lang), [config.cities, lang]);
  const [values, setValues] = useState(EMPTY);
  const [honeypot, setHoneypot] = useState('');
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
  const err = (field) => (touched[field] && errors[field] ? t(errors[field]) : undefined);

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
    onSubmit(
      {
        fullName: values.fullName.trim(),
        phone: normalizeMoroccanPhone(values.phone),
        city: values.city === OTHER_CITY ? values.otherCity.trim().replace(/\s+/g, ' ') : values.city,
        address: values.address.trim(),
      },
      { website: honeypot },
    );
  };

  return (
    <form className="checkout-form" onSubmit={handleSubmit} noValidate>
      <section className="checkout-section">
        <h2>{t('form.shipping')}</h2>
        <Field id="fullName" label={t('form.name')} error={err('fullName')}>
          <input id="fullName" autoComplete="name" placeholder={t('form.namePh')} value={values.fullName}
            onChange={update('fullName')} onBlur={blur('fullName')} {...a11y('fullName')} />
        </Field>
        <Field id="phone" label={t('form.phone')} error={err('phone')}>
          <input id="phone" type="tel" inputMode="tel" autoComplete="tel" placeholder="06 XX XX XX XX" value={values.phone}
            onChange={update('phone')} onBlur={blur('phone')} {...a11y('phone')} />
        </Field>
        <Field id="city" label={t('form.city')} error={err('city')}>
          <input type="search" className="checkout-form__city-search" placeholder={t('form.citySearchPh')}
            aria-label={t('form.citySearchPh')} aria-controls="city" value={citySearch} onChange={(e) => setCitySearch(e.target.value)} />
          <select id="city" value={values.city} onChange={update('city')} onBlur={blur('city')} {...a11y('city')}>
            <option value="" disabled>{t('form.cityPh')}</option>
            {cities
              .filter((c) => c.value === values.city || !citySearch.trim() || c.key.includes(searchKey(citySearch)))
              .map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            <option value={OTHER_CITY}>{t('form.otherCityOption')}</option>
          </select>
        </Field>
        {values.city === OTHER_CITY && (
          <Field id="otherCity" label={t('form.otherCity')} error={err('otherCity')}>
            <input id="otherCity" placeholder={t('form.otherCityPh')} value={values.otherCity}
              onChange={update('otherCity')} onBlur={blur('otherCity')} {...a11y('otherCity')} />
          </Field>
        )}
        <Field id="address" label={t('form.address')} error={err('address')}>
          <input id="address" autoComplete="street-address" placeholder={t('form.addressPh')} value={values.address}
            onChange={update('address')} onBlur={blur('address')} {...a11y('address')} />
        </Field>
      </section>

      <section className="checkout-section">
        <h2>{t('form.deliveryMode')}</h2>
        <div className="option-card is-selected">
          <Truck size={24} strokeWidth={1.5} />
          <div>
            <strong>{t('form.home')}</strong>
            <span>{t('form.everywhere')}</span>
          </div>
          <span className="option-card__price">{deliveryFee === 0 ? t('form.free') : formatPrice(deliveryFee)}</span>
        </div>
      </section>

      <section className="checkout-section">
        <h2>{t('form.paymentMode')}</h2>
        <div className="option-card is-selected">
          <HandCoins size={24} strokeWidth={1.5} />
          <div>
            <strong>{t('form.cod')}</strong>
            <span>{t('form.codText')}</span>
          </div>
        </div>
      </section>

      {children}

      {/* Champ piège anti-robots (mode API) : invisible et ignoré par les humains et les lecteurs d'écran. */}
      {!ORDERS_ARE_SIMULATED && (
        <div className="hp-field" aria-hidden="true">
          <label htmlFor="website">{t('common.honeypot')}</label>
          <input id="website" name="website" tabIndex={-1} autoComplete="off" value={honeypot}
            onChange={(e) => setHoneypot(e.target.value)} />
        </div>
      )}

      {alert}

      <div className="sticky-actions">
        <button type="submit" className="btn btn--primary btn--lg btn--block" disabled={submitting} aria-busy={submitting}>
          {submitting ? (<><Loader2 size={18} className="spin" /> {t('form.sending')}</>) : t('form.submit')}
        </button>
        <p className="secure-note">
          <Lock size={13} />{' '}
          {ORDERS_ARE_SIMULATED
            ? t('form.demoNote')
            : t('form.privacyNote')}
        </p>
      </div>
    </form>
  );
}
