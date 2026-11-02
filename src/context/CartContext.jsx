import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useCatalog } from './CatalogContext.jsx';
import { MAX_QTY, clampQty, loadCart, saveCart, loadPromo, savePromo, toItem } from '../services/cartService.js';
import { findVariant, lineKey, unitPrice } from '../utils/variants.js';
import { productParams, track } from '../analytics/metaPixel.js';
import { loadFavorites, saveFavorites } from '../services/favoritesService.js';
import { resolveLocalPromo } from '../utils/pricing.js';
import { DATA_SOURCE } from '../config/env.js';
import { validatePromo } from '../services/orderService.js';
import { useI18n } from '../i18n/I18nContext.jsx';

const isLocal = DATA_SOURCE === 'local';

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { status, getProductById, config } = useCatalog();
  const { t, lang } = useI18n();
  const [items, setItems] = useState(loadCart);
  const [promo, setPromo] = useState(() => {
    const saved = loadPromo();
    // Ancien format (simple code) : recalculé en mode démo, abandonné en mode API (le client le ressaisit).
    if (saved?.legacy) return isLocal ? resolveLocalPromo(saved.code) : null;
    return saved;
  });
  const [favorites, setFavorites] = useState(loadFavorites);

  // Une fois le catalogue prêt, on retire les produits (ou variantes) qui n'existent plus.
  useEffect(() => {
    if (status !== 'ready') return;
    setItems((prev) => {
      const kept = prev.filter((i) => {
        const product = getProductById(i.id);
        return product && (i.variantId == null || findVariant(product, i.variantId));
      });
      return kept.length === prev.length ? prev : kept;
    });
  }, [status, getProductById]);

  useEffect(() => saveCart(items), [items]);
  useEffect(() => savePromo(promo), [promo]);
  useEffect(() => saveFavorites(favorites), [favorites]);

  /** `variantId` : variante choisie (mode API) ; même produit + même variante = même ligne. */
  const addItem = useCallback((id, qty = 1, variantId) => {
    const item = toItem(id, qty, variantId);
    const key = lineKey(item);
    setItems((prev) => {
      const existing = prev.find((i) => lineKey(i) === key);
      if (existing) return prev.map((i) => (lineKey(i) === key ? { ...i, qty: clampQty(i.qty + qty) } : i));
      return [...prev, item];
    });
    // Pixel Meta (hors du calcul d'état : jamais compté deux fois) — prix réel du catalogue.
    const product = getProductById(id);
    if (product) track('AddToCart', productParams(product, unitPrice(product, findVariant(product, item.variantId) || null), item.qty));
  }, [getProductById]);

  /** `key` = lineKey(ligne) — l'identifiant du produit pour une ligne sans variante. */
  const setQty = useCallback((key, qty) => {
    setItems((prev) => prev.map((i) => (lineKey(i) === key ? { ...i, qty: clampQty(qty) } : i)));
  }, []);

  const removeItem = useCallback((key) => {
    const line = items.find((i) => lineKey(i) === key);
    setItems((prev) => prev.filter((i) => lineKey(i) !== key));
    const product = line && getProductById(line.id);
    // « RemoveFromCart » n'est pas un événement standard Meta : envoyé en événement personnalisé.
    if (product) track('RemoveFromCart', productParams(product, unitPrice(product, findVariant(product, line.variantId) || null), line.qty));
  }, [items, getProductById]);

  const clearCart = useCallback(() => {
    setItems([]);
    setPromo(null);
  }, []);

  /**
   * Applique un code. Retourne { ok, message }.
   * Mode démo : codes de src/config/store.js · Mode API : vérifié par le serveur (revérifié à la commande).
   */
  const applyPromo = useCallback(
    async (code) => {
      if (isLocal) {
        const local = resolveLocalPromo(code, config);
        if (!local) return { ok: false, message: t('cart.promoInvalid') };
        setPromo(local);
        return { ok: true };
      }
      try {
        const result = await validatePromo(code.trim(), items);
        // Message précis du serveur (en français) ; en arabe, message traduit.
        if (!result.ok) return { ok: false, message: (lang === 'fr' && result.message) || t('cart.promoInvalid') };
        setPromo(result.promo);
        return { ok: true };
      } catch {
        return { ok: false, message: t('cart.promoCheckFailed') };
      }
    },
    [config, items, t, lang],
  );

  const removePromo = useCallback(() => setPromo(null), []);

  const toggleFavorite = useCallback((id) => {
    const adding = !favorites.includes(id);
    setFavorites((prev) => (prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]));
    const product = adding && getProductById(id);
    if (product) track('AddToWishlist', productParams(product, product.price));
  }, [favorites, getProductById]);

  const value = useMemo(
    () => ({
      items,
      count: items.reduce((s, i) => s + i.qty, 0),
      addItem,
      setQty,
      removeItem,
      clearCart,
      promo,
      promoCode: promo?.code || '',
      applyPromo,
      removePromo,
      favorites,
      toggleFavorite,
      maxQty: MAX_QTY,
    }),
    [items, promo, favorites, addItem, setQty, removeItem, clearCart, applyPromo, removePromo, toggleFavorite],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart doit être utilisé dans <CartProvider>');
  return ctx;
}
