const TZ = 'Africa/Casablanca';
const moneyFmt = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const intFmt = new Intl.NumberFormat('fr-FR');

export const formatMoney = (value) => (value == null ? '—' : `${moneyFmt.format(Number(value))} DH`);
export const formatInt = (value) => (value == null ? '—' : intFmt.format(value));

export function formatDate(iso, { time = true } = {}) {
  if (!iso) return '—';
  return new Intl.DateTimeFormat('fr-FR', {
    timeZone: TZ, day: '2-digit', month: 'short', year: 'numeric', ...(time ? { hour: '2-digit', minute: '2-digit' } : {}),
  }).format(new Date(iso));
}

/** Date du jour au Maroc, AAAA-MM-JJ (filtres de période). */
export function todayIso(offsetDays = 0) {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
    .format(new Date(Date.now() + offsetDays * 86400000));
  return parts; // en-CA donne déjà AAAA-MM-JJ
}

/** +212612345678 → 06 12 34 56 78 */
export function formatPhone(e164) {
  const match = /^\+212(\d)(\d{2})(\d{2})(\d{2})(\d{2})$/.exec(e164 || '');
  return match ? `0${match[1]} ${match[2]} ${match[3]} ${match[4]} ${match[5]}` : e164 || '—';
}

/** Lien WhatsApp vers le client (+212… → wa.me/212…). */
export function whatsappLink(e164, message = '') {
  const digits = (e164 || '').replace(/\D/g, '');
  if (!digits) return null;
  return `https://wa.me/${digits}${message ? `?text=${encodeURIComponent(message)}` : ''}`;
}

export const ORDER_STATUS = {
  pending: { label: 'En attente', tone: 'warning' },
  confirmed: { label: 'Confirmée', tone: 'info' },
  shipped: { label: 'Expédiée', tone: 'info' },
  delivered: { label: 'Livrée', tone: 'success' },
  cancelled: { label: 'Annulée', tone: 'muted' },
  returned: { label: 'Retournée', tone: 'danger' },
};

/** Libellé du bouton qui fait passer la commande à ce statut. */
export const STATUS_ACTION = {
  confirmed: 'Confirmer la commande',
  shipped: 'Marquer comme expédiée',
  delivered: 'Marquer comme livrée',
  cancelled: 'Annuler la commande',
  returned: 'Enregistrer un retour',
};

export const PAYMENT_STATUS = {
  unpaid: { label: 'Non payée', tone: 'warning' },
  paid: { label: 'Payée', tone: 'success' },
  refunded: { label: 'Remboursée', tone: 'muted' },
};

export const STOCK_STATE = {
  unknown: { label: 'Non renseigné', tone: 'neutral-dashed' },
  out_of_stock: { label: 'Rupture', tone: 'danger' },
  low: { label: 'Stock bas', tone: 'warning' },
  ok: { label: 'En stock', tone: 'success' },
  not_tracked: { label: 'Non suivi', tone: 'muted' },
};

export const ROLE_LABELS = {
  owner: 'Propriétaire',
  admin: 'Administrateur',
  order_manager: 'Gestionnaire de commandes',
  content_editor: 'Éditeur de contenu',
  analyst: 'Analyste',
};

export const MOVEMENT_REASONS = {
  initial_count: 'Premier comptage',
  recount: 'Inventaire (recomptage)',
  restock: 'Réception de stock',
  manual_adjustment: 'Correction manuelle',
  damaged: 'Abîmé / perdu',
  order_placed: 'Commande passée',
  order_cancelled: 'Commande annulée',
  order_returned: 'Commande retournée',
};
