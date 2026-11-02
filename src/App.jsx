import { lazy, Suspense } from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import HomePage from './pages/HomePage.jsx';
import ScrollToTop from './components/ScrollToTop.jsx';
import { CatalogProvider, useCatalog } from './context/CatalogContext.jsx';
import { CartProvider } from './context/CartContext.jsx';
import { ThemeProvider, useTheme } from './theme/ThemeContext.jsx';
import ThemePreviewBridge from './theme/ThemePreviewBridge.jsx';
import { I18nProvider, useI18n } from './i18n/I18nContext.jsx';
import MetaPixelTracker from './analytics/MetaPixelTracker.jsx';

const ProductsPage = lazy(() => import('./pages/ProductsPage.jsx'));
const ProductPage = lazy(() => import('./pages/ProductPage.jsx'));
const CartPage = lazy(() => import('./pages/CartPage.jsx'));
const CheckoutPage = lazy(() => import('./pages/CheckoutPage.jsx'));
const ConfirmationPage = lazy(() => import('./pages/ConfirmationPage.jsx'));
// Administration : chargée à part, uniquement quand on visite /admin (n'alourdit pas la boutique).
const AdminApp = lazy(() => import('./admin/AdminApp.jsx'));

function NotFound() {
  const { t } = useI18n();
  return (
    <main className="container empty-state">
      <h1>{t('notFound.title')}</h1>
      <Link className="btn btn--primary" to="/">{t('notFound.back')}</Link>
    </main>
  );
}

/** Mode API uniquement : attente puis erreur du chargement du catalogue. */
function CatalogGate({ children }) {
  const { status, retry } = useCatalog();
  const theme = useTheme();
  const { t } = useI18n();
  if (status === 'ready' && theme.status === 'ready') return children;
  if (status === 'error') {
    return (
      <main className="container empty-state" role="alert">
        <h1>{t('catalog.errorTitle')}</h1>
        <p>{t('catalog.errorText')}</p>
        <button type="button" className="btn btn--primary" onClick={retry}>{t('common.retry')}</button>
      </main>
    );
  }
  return <div className="page-loading" aria-label={t('common.loadingCatalog')} />;
}

/** Boutique publique. Catalogue et panier ne sont chargés qu'ici (jamais dans l'administration). */
function Storefront() {
  return (
    <I18nProvider>
      <CatalogProvider>
        <ThemeProvider>
          <CartProvider>
            <StorefrontRoutes />
            <ThemePreviewBridge />
            <MetaPixelTracker />
          </CartProvider>
        </ThemeProvider>
      </CatalogProvider>
    </I18nProvider>
  );
}

function StorefrontRoutes() {
  const { t } = useI18n();
  return (
    <div className="app">
      <CatalogGate>
      <Suspense fallback={<div className="page-loading" aria-label={t('common.loading')} />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/produits" element={<ProductsPage />} />
          <Route path="/produits/:id" element={<ProductPage />} />
          <Route path="/panier" element={<CartPage />} />
          <Route path="/commande" element={<CheckoutPage />} />
          <Route path="/confirmation" element={<ConfirmationPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
      </CatalogGate>
    </div>
  );
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route
          path="/admin/*"
          element={(
            <Suspense fallback={<div className="page-loading" aria-label="Chargement" />}>
              <AdminApp />
            </Suspense>
          )}
        />
        <Route path="*" element={<Storefront />} />
      </Routes>
    </>
  );
}
