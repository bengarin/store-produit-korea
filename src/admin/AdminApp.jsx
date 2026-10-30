import { lazy, Suspense, useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Settings2 } from 'lucide-react';
import './admin.css';
import { ADMIN_API_READY } from './api.js';
import { AuthProvider, RequireAuth, useAuth } from './auth.jsx';
import Layout from './components/Layout.jsx';
import { EmptyState, ErrorState, PageLoader } from './components/ui.jsx';
import { can, homePath } from './permissions.js';
import LoginPage from './pages/LoginPage.jsx';

const DashboardPage = lazy(() => import('./pages/DashboardPage.jsx'));
const OrdersPage = lazy(() => import('./pages/OrdersPage.jsx'));
const OrderDetailPage = lazy(() => import('./pages/OrderDetailPage.jsx'));
const CustomersPage = lazy(() => import('./pages/CustomersPage.jsx'));
const CustomerDetailPage = lazy(() => import('./pages/CustomerDetailPage.jsx'));
const InventoryPage = lazy(() => import('./pages/InventoryPage.jsx'));
const SettingsPage = lazy(() => import('./pages/SettingsPage.jsx'));

/** Page réservée à certains rôles (le serveur refuse de toute façon). */
function Allow({ perm, children }) {
  const { user } = useAuth();
  if (!can(user, perm)) return <ErrorState error={{ status: 403 }} />;
  return children;
}

function Home() {
  const { user } = useAuth();
  return <Navigate to={homePath(user)} replace />;
}

function NotConfigured() {
  return (
    <div className="adm-root adm-center">
      <EmptyState
        icon={Settings2}
        title="Administration non configurée"
        text="Démarrez le backend puis définissez VITE_API_BASE_URL (ou VITE_ADMIN_API_BASE_URL) — voir backend/README.md."
      />
    </div>
  );
}

function AdminRoutes() {
  const { status, error, retry } = useAuth();
  if (status === 'error') {
    return <div className="adm-root adm-center"><ErrorState error={error} onRetry={retry} /></div>;
  }
  return (
    <Routes>
      <Route path="login" element={<LoginPage />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Home />} />
        <Route path="dashboard" element={<Allow perm="viewDashboard"><DashboardPage /></Allow>} />
        <Route path="orders" element={<Allow perm="viewOrders"><OrdersPage /></Allow>} />
        <Route path="orders/:id" element={<Allow perm="viewOrders"><OrderDetailPage /></Allow>} />
        <Route path="customers" element={<Allow perm="viewCustomers"><CustomersPage /></Allow>} />
        <Route path="customers/:id" element={<Allow perm="viewCustomers"><CustomerDetailPage /></Allow>} />
        <Route path="inventory" element={<Allow perm="viewInventory"><InventoryPage /></Allow>} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Home />} />
      </Route>
    </Routes>
  );
}

export default function AdminApp() {
  useEffect(() => {
    // Pas d'indexation par les moteurs de recherche ; titre rétabli en revenant sur la boutique.
    const meta = document.createElement('meta');
    meta.name = 'robots';
    meta.content = 'noindex, nofollow';
    document.head.appendChild(meta);
    const previousTitle = document.title;
    return () => {
      meta.remove();
      document.title = previousTitle;
    };
  }, []);

  if (!ADMIN_API_READY) return <NotConfigured />;
  return (
    <div className="adm-root">
      <AuthProvider>
        <Suspense fallback={<PageLoader />}>
          <AdminRoutes />
        </Suspense>
      </AuthProvider>
    </div>
  );
}
