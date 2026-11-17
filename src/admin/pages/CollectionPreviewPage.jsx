import { useCallback, useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import ProductsPage from '../../pages/ProductsPage.jsx';
import { CatalogProvider } from '../../context/CatalogContext.jsx';
import { CartPreviewProvider } from '../../context/CartContext.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { I18nProvider } from '../../i18n/I18nContext.jsx';
import { normalizeProducts } from '../../services/productService.js';
import { DEMO_CATEGORIES, DEMO_FILTERS, demoCollection, demoProducts } from '../demo/collectionDemo.js';
import { useApi, useTitle } from '../hooks.js';

const BLOCKED = 'Aperçu TEST : la navigation est désactivée (produits fictifs).';

/**
 * Aperçu de DÉMONSTRATION d'une collection (« TEST — données fictives »), réservé à l'administration.
 * - Page réelle de la boutique (ProductsPage : en-tête, filtres, tri, tiroir mobile), mais avec un catalogue
 *   FICTIF en mémoire : aucun vrai produit, aucun pays de fabrication, aucun appel d'écriture au serveur.
 * - Seuls les textes et l'image de la collection sont lus (GET Admin → Collections).
 * - Panier et favoris fictifs en mémoire : le vrai panier du navigateur n'est ni lu ni modifié.
 * - Liens et recherche bloqués : on reste dans l'aperçu.
 * - Langue : ?lang=fr|ar (arabe = mise en page de droite à gauche).
 */
export default function CollectionPreviewPage() {
  const { slug } = useParams();
  const [params, setParams] = useSearchParams();
  const lang = params.get('lang') === 'ar' ? 'ar' : 'fr';
  const { data, error } = useApi('/collections');
  const showToast = useToast();
  useTitle('Aperçu TEST');

  const collection = data?.find((c) => c.slug === slug) || null;
  const preset = useMemo(() => {
    if (!collection) return null;
    const raw = demoProducts(collection.slug);
    return {
      products: normalizeProducts(raw),
      categories: DEMO_CATEGORIES,
      filters: DEMO_FILTERS,
      collections: [demoCollection(collection, raw)],
    };
  }, [collection]);

  const setLang = useCallback((next) => {
    const p = new URLSearchParams(params);
    if (next === 'ar') p.set('lang', 'ar');
    else p.delete('lang');
    setParams(p, { replace: true });
  }, [params, setParams]);

  // Liens et recherche : bloqués avant que la boutique ne les traite (phase de capture).
  const block = (e) => {
    e.preventDefault();
    e.stopPropagation();
    showToast(BLOCKED, 'info');
  };
  const onClickCapture = (e) => {
    if (e.target.closest?.('a[href]')) block(e);
  };
  const onSubmitCapture = (e) => {
    if (e.target.closest?.('.search-panel__form')) block(e);
  };

  if (error) return <div className="adm-preview-msg" role="alert">Aperçu indisponible : {error.message}</div>;
  if (!data) return <div className="adm-preview-msg">Chargement de l’aperçu…</div>;
  if (!collection) return <div className="adm-preview-msg" role="alert">Collection introuvable.</div>;

  return (
    <div className="app adm-demo" onClickCapture={onClickCapture} onSubmitCapture={onSubmitCapture}>
      <div className="adm-demo-bar" role="note">
        <p lang="fr" dir="ltr">
          <strong>TEST — données fictives</strong> · Aperçu réservé à l’administration, invisible des clients.
          Produits, prix et images inventés ; rien n’est enregistré.
        </p>
        {lang === 'ar' && (
          <p lang="ar" dir="rtl"><strong>اختبار — بيانات وهمية</strong> · معاينة خاصة بالإدارة، لا يراها العملاء.</p>
        )}
      </div>
      <I18nProvider key={lang} lang={lang} onLangChange={setLang}>
        <CatalogProvider preset={preset}>
          <DemoCart>
            <ProductsPage />
          </DemoCart>
        </CatalogProvider>
      </I18nProvider>
    </div>
  );
}

/** Panier et favoris fictifs, en mémoire uniquement (jamais enregistrés dans le navigateur). */
function DemoCart({ children }) {
  const [count, setCount] = useState(0);
  const [favorites, setFavorites] = useState([]);
  const value = useMemo(() => ({
    items: [],
    count,
    addItem: (id, qty = 1) => setCount((n) => n + qty),
    setQty: () => {},
    removeItem: () => {},
    clearCart: () => setCount(0),
    promo: null,
    promoCode: '',
    applyPromo: async () => false,
    removePromo: () => {},
    favorites,
    toggleFavorite: (id) => setFavorites((prev) => (prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id])),
    maxQty: 20,
  }), [count, favorites]);
  return <CartPreviewProvider value={value}>{children}</CartPreviewProvider>;
}
