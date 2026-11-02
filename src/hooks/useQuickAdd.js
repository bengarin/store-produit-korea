import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { defaultVariant, hasChoice, productStatus } from '../utils/variants.js';
import { useI18n } from '../i18n/I18nContext.jsx';

/**
 * Ajout rapide depuis une carte produit. Retourne true si l'article a été ajouté.
 * - produit à options : ouvre la fiche pour choisir (jamais de variante ajoutée au hasard) ;
 * - produit épuisé / indisponible : rien n'est ajouté.
 */
export default function useQuickAdd() {
  const { addItem } = useCart();
  const showToast = useToast();
  const navigate = useNavigate();
  const { t } = useI18n();
  return useCallback(
    (product) => {
      if (hasChoice(product)) {
        navigate(`/produits/${product.id}`);
        showToast(t('toast.chooseOption'), 'info');
        return false;
      }
      const status = productStatus(product);
      if (status !== 'available') {
        showToast(t('card.statusNamed', { name: product.displayName, status: t(`status.${status}`) }), 'info');
        return false;
      }
      addItem(product.id, 1, defaultVariant(product)?.id);
      showToast(t('toast.added', { name: product.displayName }));
      return true;
    },
    [addItem, navigate, showToast, t],
  );
}
