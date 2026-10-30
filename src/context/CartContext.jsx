import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useCatalog } from './CatalogContext.jsx';
import { MAX_QTY, clampQty, loadCart, saveCart, loadPromo, savePromo } from '../services/cartService.js';
import { loadFavorites, saveFavorites } from '../services/favoritesService.js';
import { resolveLocalPromo } from '../utils/pricing.js';
import { DATA_SOURCE } from '../config/env.js';
import { validatePromo } from '../services/orderService.js';

const isLocal = DATA_SOURCE === 'local';
const INVALID_PROMO = 'Ce code promo n’est pas valide.';

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { status, getProductById, config } = useCatalog();
  const [items, setItems] = useState(loadCart);
  const [promo, setPromo] = useState(() => {
    const saved = loadPromo();
    // Ancien format (simple code) : recalculé en mode démo, abandonné en mode API (le client le ressaisit).
    if (saved?.legacy) return isLocal ? resolveLocalPromo(saved.code) : null;
    return saved;
  });
  const [favorites, setFavorites] = useState(loadFavorites);

  // Une fois le catalogue prêt, on retire les produits qui n'existent plus.
  useEffect(() => {
    if (status !== 'ready') return;
    setItems((prev) => {
      const kept = prev.filter((i) => getProductById(i.id));
      return kept.length === prev.length ? prev : kept;
    });
  }, [status, getProductById]);

  useEffect(() => saveCart(items), [items]);
  useEffect(() => savePromo(promo), [promo]);
  useEffect(() => saveFavorites(favorites), [favorites]);

  const addItem = useCallback((id, qty = 1) => {
    setItems((prev) => {
      const existing = prev.find((i) => i.id === id);
      if (existing) return prev.map((i) => (i.id === id ? { ...i, qty: clampQty(i.qty + qty) } : i));
      return [...prev, { id, qty: clampQty(qty) }];
    });
  }, []);

  const setQty = useCallback((id, qty) => {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, qty: clampQty(qty) } : i)));
  }, []);

  const removeItem = useCallback((id) => setItems((prev) => prev.filter((i) => i.id !== id)), []);

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
        if (!local) return { ok: false, message: INVALID_PROMO };
        setPromo(local);
        return { ok: true };
      }
      try {
        const result = await validatePromo(code.trim(), items);
        if (!result.ok) return { ok: false, message: result.message || INVALID_PROMO };
        setPromo(result.promo);
        return { ok: true };
      } catch {
        return { ok: false, message: 'Vérification du code impossible. Réessayez.' };
      }
    },
    [config, items],
  );

  const removePromo = useCallback(() => setPromo(null), []);

  const toggleFavorite = useCallback((id) => {
    setFavorites((prev) => (prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]));
  }, []);

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
