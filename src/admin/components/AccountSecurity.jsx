import { useState } from 'react';
import { KeyRound, LogOut, ShieldCheck, ShieldOff } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import { Badge, Button, Card, Field, Notice } from './ui.jsx';
import { BackupCodes, TwoFactorSetup } from './TwoFactor.jsx';

/** Sécurité du compte : double authentification, codes de secours, autres appareils. */
export default function AccountSecurity() {
  const { twoFactor, setTwoFactor } = useAuth();
  const [mode, setMode] = useState(null); // setup | codes | disable
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [codes, setCodes] = useState(null);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);
  if (!twoFactor) return null;

  const run = async (fn) => {
    setBusy(true);
    setMessage(null);
    try {
      await fn();
    } catch (e) {
      setMessage({ tone: 'danger', text: e.message });
    } finally {
      setBusy(false);
      setPassword('');
      setCode('');
    }
  };
  const newCodes = (e) => {
    e.preventDefault();
    run(async () => { setCodes((await admin.post('/auth/2fa/backup-codes', { password })).backupCodes); setMode(null); });
  };
  const disable = (e) => {
    e.preventDefault();
    run(async () => {
      setTwoFactor((await admin.post('/auth/2fa/disable', { password, code })).twoFactor);
      setMode(null);
      setMessage({ tone: 'info', text: 'Double authentification désactivée.' });
    });
  };
  const revoke = () => run(async () => {
    const { revoked } = await admin.post('/auth/sessions/revoke');
    setMessage({ tone: 'success', text: revoked ? `${revoked} autre(s) appareil(s) déconnecté(s).` : 'Aucun autre appareil connecté.' });
  });

  return (
    <Card title={<><ShieldCheck size={17} aria-hidden="true" /> Sécurité du compte</>}
      actions={twoFactor.enabled ? <Badge tone="success">2FA activée</Badge> : <Badge tone="warning">2FA désactivée</Badge>}>
      <p className="adm-muted">
        La double authentification demande, en plus du mot de passe, un code de votre téléphone.
        {twoFactor.required && ' Elle est obligatoire pour votre rôle.'}
        {twoFactor.enabled && ` Codes de secours restants : ${twoFactor.backupCodesLeft}.`}
      </p>
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      {codes && <BackupCodes codes={codes} onDone={() => { setCodes(null); setTwoFactor({ ...twoFactor, backupCodesLeft: codes.length }); }} />}
      {mode === 'setup' && <TwoFactorSetup onEnabled={(t) => { setTwoFactor(t); setMode(null); }} />}
      {mode === 'codes' && (
        <form onSubmit={newCodes} noValidate className="adm-stack">
          <Field label="Mot de passe" htmlFor="sec-pass"><input id="sec-pass" type="password" className="adm-input" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
          <Notice tone="warning">Les anciens codes de secours ne fonctionneront plus.</Notice>
          <Button type="submit" loading={busy} disabled={!password}>Générer de nouveaux codes</Button>
        </form>
      )}
      {mode === 'disable' && (
        <form onSubmit={disable} noValidate className="adm-stack">
          <Field label="Mot de passe" htmlFor="sec-pass2"><input id="sec-pass2" type="password" className="adm-input" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
          <Field label="Code actuel de l’application" htmlFor="sec-code"><input id="sec-code" className="adm-input" inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} /></Field>
          <Button type="submit" variant="danger" loading={busy} disabled={!password || !code}>Désactiver</Button>
        </form>
      )}
      {!mode && !codes && (
        <div className="adm-actions-row adm-mt">
          {!twoFactor.enabled && <Button icon={ShieldCheck} onClick={() => setMode('setup')}>Activer la double authentification</Button>}
          {twoFactor.enabled && <Button variant="secondary" icon={KeyRound} onClick={() => setMode('codes')}>Nouveaux codes de secours</Button>}
          {twoFactor.enabled && !twoFactor.required && <Button variant="danger-ghost" icon={ShieldOff} onClick={() => setMode('disable')}>Désactiver</Button>}
          <Button variant="ghost" icon={LogOut} loading={busy} onClick={revoke}>Déconnecter mes autres appareils</Button>
        </div>
      )}
    </Card>
  );
}
