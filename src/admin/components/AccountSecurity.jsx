import { useState } from 'react';
import { LogOut, ShieldCheck } from 'lucide-react';
import { admin } from '../api.js';
import { Button, Card, Notice } from './ui.jsx';

/** Sécurité du compte : fermer les sessions ouvertes sur les autres appareils (la session en cours reste ouverte). */
export default function AccountSecurity() {
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  const revoke = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const { revoked } = await admin.post('/auth/sessions/revoke');
      setMessage({ tone: 'success', text: revoked ? `${revoked} autre(s) appareil(s) déconnecté(s).` : 'Aucun autre appareil connecté.' });
    } catch (e) {
      setMessage({ tone: 'danger', text: e.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title={<><ShieldCheck size={17} aria-hidden="true" /> Sécurité du compte</>}>
      <p className="adm-muted">Ordinateur ou téléphone perdu, mot de passe partagé par erreur : fermez les sessions ouvertes ailleurs.</p>
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      <div className="adm-actions-row adm-mt">
        <Button variant="ghost" icon={LogOut} loading={busy} onClick={revoke}>Déconnecter mes autres appareils</Button>
      </div>
    </Card>
  );
}
