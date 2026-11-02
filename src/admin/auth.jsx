import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { admin, setUnauthenticatedHandler } from './api.js';
import { TwoFactorGate } from './components/TwoFactor.jsx';
import { PageLoader } from './components/ui.jsx';

const AuthContext = createContext(null);

/** N'accepte qu'une redirection interne à l'administration (pas de redirection ouverte). */
export function safeNext(value) {
  return typeof value === 'string' && /^\/admin\/[\w\-/?=&%.]*$/.test(value) && !value.startsWith('//') ? value : null;
}

export function AuthProvider({ children }) {
  // status : 'loading' | 'authenticated' | 'anonymous' | 'error'
  // twoFactor : { enabled, required, status: 'verified' | 'required' | 'setup_required', backupCodesLeft }
  const [state, setState] = useState({ status: 'loading', user: null, twoFactor: null, expired: false, error: null });

  const loadMe = useCallback(async () => {
    setState((s) => ({ ...s, status: 'loading', error: null }));
    try {
      const { user, twoFactor } = await admin.get('/auth/me');
      setState({ status: 'authenticated', user, twoFactor, expired: false, error: null });
    } catch (error) {
      if (error.code === 'not_authenticated' || error.status === 403 || error.status === 401) {
        setState({ status: 'anonymous', user: null, expired: false, error: null });
      } else {
        setState({ status: 'error', user: null, expired: false, error });
      }
    }
  }, []);

  useEffect(() => {
    loadMe();
    // Session expirée pendant l'utilisation : on bascule vers la page de connexion.
    setUnauthenticatedHandler((code) => {
      // Code 2FA demandé par le serveur (ex. autre onglet) : on relit l'état ; sinon session expirée.
      if (code === 'otp_required' || code === 'otp_setup_required') {
        setState((s) => (s.twoFactor ? { ...s, twoFactor: { ...s.twoFactor, status: code === 'otp_required' ? 'required' : 'setup_required' } } : s));
        return;
      }
      setState((s) => (s.status === 'authenticated' ? { status: 'anonymous', user: null, twoFactor: null, expired: true, error: null } : s));
    });
    return () => setUnauthenticatedHandler(null);
  }, [loadMe]);

  const login = useCallback(async (email, password) => {
    await admin.get('/auth/csrf'); // dépose le cookie CSRF avant le POST
    const { user, twoFactor } = await admin.post('/auth/login', { email, password });
    setState({ status: 'authenticated', user, twoFactor, expired: false, error: null });
    return { ...user, twoFactor };
  }, []);

  const verifyCode = useCallback(async (code) => {
    const { twoFactor } = await admin.post('/auth/2fa/verify', { code });
    setState((s) => ({ ...s, twoFactor }));
  }, []);
  const setTwoFactor = useCallback((twoFactor) => setState((s) => ({ ...s, twoFactor })), []);

  const logout = useCallback(async () => {
    try {
      await admin.post('/auth/logout');
    } finally {
      setState({ status: 'anonymous', user: null, twoFactor: null, expired: false, error: null });
    }
  }, []);

  const value = useMemo(
    () => ({ ...state, login, logout, verifyCode, setTwoFactor, retry: loadMe }),
    [state, login, logout, verifyCode, setTwoFactor, loadMe],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth doit être utilisé dans <AuthProvider>');
  return ctx;
}

/** Protège une zone : redirige vers /admin/login (en gardant la page demandée). */
export function RequireAuth({ children }) {
  const { status, expired, twoFactor } = useAuth();
  const location = useLocation();
  if (status === 'loading') return <PageLoader label="Vérification de la session…" />;
  if (status !== 'authenticated') {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/admin/login?next=${next}${expired ? '&expired=1' : ''}`} replace />;
  }
  // Mot de passe correct mais code 2FA attendu (ou 2FA obligatoire à activer) : rien d'autre n'est affiché.
  if (twoFactor && twoFactor.status !== 'verified') return <div className="adm-root"><TwoFactorGate /></div>;
  return children;
}
