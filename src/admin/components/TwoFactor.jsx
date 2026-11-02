import { useState } from 'react';
import { KeyRound, LogOut, ShieldCheck } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import { Button, Field, Notice } from './ui.jsx';

/** Saisie d'un code : 6 chiffres de l'application, ou un code de secours (8 chiffres). */
function CodeInput({ id, value, onChange }) {
  return (
    <input id={id} className="adm-input adm-otp-input" inputMode="numeric" autoComplete="one-time-code" maxLength={12}
      value={value} onChange={(e) => onChange(e.target.value.replace(/[^\d ]/g, ''))} placeholder="123 456" />
  );
}

/** Codes de secours : affichés une seule fois, à noter avant de continuer. */
export function BackupCodes({ codes, onDone }) {
  const [saved, setSaved] = useState(false);
  return (
    <div className="adm-otp-codes">
      <Notice tone="warning" icon={KeyRound}>
        Notez ces <strong>10 codes de secours</strong> et rangez-les en lieu sûr (hors du téléphone). Chacun permet
        une seule connexion si vous perdez votre téléphone. Ils ne seront <strong>plus jamais affichés</strong>.
      </Notice>
      <ol className="adm-otp-codes__list">{codes.map((c) => <li key={c}><code>{c.slice(0, 4)} {c.slice(4)}</code></li>)}</ol>
      <label className="adm-check"><input type="checkbox" checked={saved} onChange={(e) => setSaved(e.target.checked)} /> J’ai noté mes codes de secours</label>
      <Button disabled={!saved} onClick={onDone}>Continuer</Button>
    </div>
  );
}

/** Activation : QR code (ou clé manuelle) → premier code → codes de secours. */
export function TwoFactorSetup({ onEnabled }) {
  const [step, setStep] = useState(null); // { otpauthUri, qrDataUri, secret }
  const [code, setCode] = useState('');
  const [codes, setCodes] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const start = async () => {
    setBusy(true);
    setError('');
    try {
      setStep(await admin.post('/auth/2fa/setup'));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const confirm = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const r = await admin.post('/auth/2fa/confirm', { code });
      setCodes({ list: r.backupCodes, twoFactor: r.twoFactor });
    } catch (err) {
      setError(err.message);
      setCode('');
    } finally {
      setBusy(false);
    }
  };

  if (codes) return <BackupCodes codes={codes.list} onDone={() => onEnabled(codes.twoFactor)} />;
  if (!step) {
    return (
      <div className="adm-otp-setup">
        <p>Installez une application d’authentification sur votre téléphone (Google Authenticator, Microsoft Authenticator, Aegis…), puis cliquez sur « Commencer ».</p>
        {error && <Notice tone="danger">{error}</Notice>}
        <Button icon={ShieldCheck} loading={busy} onClick={start}>Commencer</Button>
      </div>
    );
  }
  return (
    <form className="adm-otp-setup" onSubmit={confirm} noValidate>
      <ol className="adm-otp-steps">
        <li>Scannez ce QR code avec l’application :</li>
      </ol>
      {/* Image SVG produite par le serveur (segno), affichée dans <img> : jamais injectée dans la page. */}
      <img className="adm-otp-qr" src={step.qrDataUri.startsWith('data:image/svg+xml') ? step.qrDataUri : ''} alt="QR code de configuration de la double authentification" width="220" height="220" />
      <p className="adm-muted">Impossible de scanner ? Saisissez cette clé dans l’application : <code className="adm-otp-secret">{step.secret.match(/.{1,4}/g).join(' ')}</code></p>
      <Field label="Code à 6 chiffres affiché par l’application" htmlFor="otp-setup-code">
        <CodeInput id="otp-setup-code" value={code} onChange={setCode} />
      </Field>
      {error && <Notice tone="danger">{error}</Notice>}
      <Button type="submit" loading={busy} disabled={code.replace(/\s/g, '').length < 6}>Activer la double authentification</Button>
    </form>
  );
}

/**
 * Écran plein après le mot de passe : saisie du code (2FA active) ou activation obligatoire (rôle concerné).
 */
export function TwoFactorGate() {
  const { twoFactor, verifyCode, setTwoFactor, logout, user } = useAuth();
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const setup = twoFactor?.status === 'setup_required';

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await verifyCode(code);
    } catch (err) {
      setError(err.status === 429 ? err.message : 'Code incorrect ou expiré. Réessayez.');
      setCode('');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="adm-login">
      <div className="adm-login__card adm-login__card--wide">
        <h1><ShieldCheck size={22} aria-hidden="true" /> Double authentification</h1>
        <p className="adm-login__lead">{user?.email}</p>
        {setup ? (
          <>
            <Notice tone="info">Votre rôle exige la double authentification. Activez-la pour accéder à l’administration.</Notice>
            <TwoFactorSetup onEnabled={setTwoFactor} />
          </>
        ) : (
          <form onSubmit={submit} noValidate>
            <Field label="Code de votre application (ou code de secours)" htmlFor="otp-code">
              <CodeInput id="otp-code" value={code} onChange={setCode} />
            </Field>
            {error && <Notice tone="danger">{error}</Notice>}
            <Button type="submit" loading={busy} disabled={code.replace(/\s/g, '').length < 6} className="adm-btn--block">Valider</Button>
          </form>
        )}
        <button type="button" className="adm-link-btn adm-mt" onClick={logout}><LogOut size={14} aria-hidden="true" /> Se déconnecter</button>
      </div>
    </div>
  );
}
