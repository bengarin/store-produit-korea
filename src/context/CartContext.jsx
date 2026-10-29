import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useCatalog } from './CatalogContext.jsx';
import { MAX_QTY, clampQty, loadCart, saveCart, loadPromoCode, savePromoCode } from '../services/cartService.js';
import { loadFavorites, saveFavorites } from '../services/favoritesService.js';
import { getPromoPercent } from '../utils/pricing.js';

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { status, getProductById } = useCatalog();
  const [items, setItems] = useState(loadCart);
  const [promoCode, setPromoCode] = useState(loadPromoCode);
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
  useEffect(() => savePromoCode(promoCode), [promoCode]);
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
    setPromoCode('');
  }, []);

  /** Retourne true si le code est valide (contrôle local d'affichage ; le backend devra revalider). */
  const applyPromo = useCallback((code) => {
    const normalized = code.trim().toUpperCase();
    if (!getPromoPercent(normalized)) return false;
    setPromoCode(normalized);
    return true;
  }, []);

  const removePromo = useCallback(() => setPromoCode(''), []);

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
      promoCode,
      applyPromo,
      removePromo,
      favorites,
      toggleFavorite,
      maxQty: MAX_QTY,
    }),
    [items, promoCode, favorites, addItem, setQty, removeItem, clearCart, applyPromo, removePromo, toggleFavorite],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart doit être utilisé dans <CartProvider>');
  return ctx;
}
