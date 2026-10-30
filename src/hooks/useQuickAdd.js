import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { STATUS_LABELS, defaultVariant, hasChoice, productStatus } from '../utils/variants.js';

/**
 * Ajout rapide depuis une carte produit. Retourne true si l'article a été ajouté.
 * - produit à options : ouvre la fiche pour choisir (jamais de variante ajoutée au hasard) ;
 * - produit épuisé / indisponible : rien n'est ajouté.
 */
export default function useQuickAdd() {
  const { addItem } = useCart();
  const showToast = useToast();
  const navigate = useNavigate();
  return useCallback(
    (product) => {
      if (hasChoice(product)) {
        navigate(`/produits/${product.id}`);
        showToast('Choisissez une option', 'info');
        return false;
      }
      const status = productStatus(product);
      if (status !== 'available') {
        showToast(`${product.displayName} : ${STATUS_LABELS[status].toLowerCase()}`, 'info');
        return false;
      }
      addItem(product.id, 1, defaultVariant(product)?.id);
      showToast(`${product.displayName} ajouté au panier`);
      return true;
    },
    [addItem, navigate, showToast],
  );
}
