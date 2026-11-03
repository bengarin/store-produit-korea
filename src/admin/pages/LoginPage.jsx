import { useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { Clock, Lock, LogIn } from 'lucide-react';
import logo from '../../assets/brand/logo-full.webp';
import { safeNext, useAuth } from '../auth.jsx';
import { Button, Field, Notice } from '../components/ui.jsx';
import { useTitle } from '../hooks.js';
import { homePath } from '../permissions.js';

export default function LoginPage() {
  useTitle('Connexion');
  const { status, user, login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const next = safeNext(params.get('next'));

  if (status === 'authenticated') return <Navigate to={next || homePath(user)} replace />;

  const submit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) return setError('Saisissez votre e-mail et votre mot de passe.');
    setBusy(true);
    setError('');
    try {
      const signedIn = await login(email.trim(), password);
      navigate(next || homePath(signedIn), { replace: true });
    } catch (err) {
      setPassword('');
      setError(err.status === 401 || err.status === 429 || err.status === 400 ? err.message : `Connexion impossible : ${err.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="adm-login">
      <form className="adm-login__card" onSubmit={submit} noValidate>
        <img src={logo} alt="Ma Petite Corée.ma" className="adm-login__logo" width="180" height="129" />
        <h1>Administration</h1>
        <p className="adm-login__lead">Connectez-vous pour gérer les commandes et le stock.</p>
        {params.get('expired') && (
          <Notice tone="warning" icon={Clock}>Votre session a expiré. Reconnectez-vous pour continuer.</Notice>
        )}
        {error && <Notice tone="danger">{error}</Notice>}
        <Field label="E-mail" htmlFor="adm-email">
          <input id="adm-email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)}
            className="adm-input" />
        </Field>
        <Field label="Mot de passe" htmlFor="adm-password">
          <input id="adm-password" type="password" autoComplete="current-password" value={password}
            onChange={(e) => setPassword(e.target.value)} className="adm-input" />
        </Field>
        <Button type="submit" icon={LogIn} loading={busy} className="adm-btn--block">Se connecter</Button>
        <p className="adm-login__foot"><Lock size={13} aria-hidden="true" /> Connexion sécurisée — accès réservé à l’équipe.</p>
      </form>
    </div>
  );
}
