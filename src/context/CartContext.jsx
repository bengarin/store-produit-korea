import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getProductById } from '../data/products.js';
import { readJSON, writeJSON, safeLocal } from '../utils/storage.js';
import { getPromoPercent } from '../utils/order.js';

const CART_KEY = 'nature.cart';
const PROMO_KEY = 'nature.promo';
const FAV_KEY = 'nature.favorites';
const MAX_QTY = 20;

const CartContext = createContext(null);

const clampQty = (q) => Math.max(1, Math.min(MAX_QTY, Math.floor(q) || 1));

function loadCart() {
  const raw = readJSON(safeLocal(), CART_KEY, []);
  // On ignore les produits qui n'existent plus dans le catalogue.
  return Array.isArray(raw)
    ? raw.filter((i) => i && getProductById(i.id)).map((i) => ({ id: i.id, qty: clampQty(i.qty) }))
    : [];
}

export function CartProvider({ children }) {
  const [items, setItems] = useState(loadCart);
  const [promoCode, setPromoCode] = useState(() => readJSON(safeLocal(), PROMO_KEY, ''));
  const [favorites, setFavorites] = useState(() => readJSON(safeLocal(), FAV_KEY, []));

  useEffect(() => {
    writeJSON(safeLocal(), CART_KEY, items);
  }, [items]);
  useEffect(() => {
    writeJSON(safeLocal(), PROMO_KEY, promoCode);
  }, [promoCode]);
  useEffect(() => {
    writeJSON(safeLocal(), FAV_KEY, favorites);
  }, [favorites]);

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

  /** Retourne true si le code est valide. */
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
