import { lazy, Suspense } from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import HomePage from './pages/HomePage.jsx';
import ScrollToTop from './components/ScrollToTop.jsx';

const ProductsPage = lazy(() => import('./pages/ProductsPage.jsx'));
const ProductPage = lazy(() => import('./pages/ProductPage.jsx'));
const CartPage = lazy(() => import('./pages/CartPage.jsx'));
const CheckoutPage = lazy(() => import('./pages/CheckoutPage.jsx'));
const ConfirmationPage = lazy(() => import('./pages/ConfirmationPage.jsx'));

function NotFound() {
  return (
    <main className="container empty-state">
      <h1>Page introuvable</h1>
      <Link className="btn btn--primary" to="/">Retour à l’accueil</Link>
    </main>
  );
}

export default function App() {
  return (
    <div className="app">
      <ScrollToTop />
      <Suspense fallback={<div className="page-loading" aria-label="Chargement" />}>
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
    </div>
  );
}
