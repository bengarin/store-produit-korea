/**
 * Affichage selon le rôle : sert UNIQUEMENT à masquer ce que l'utilisateur ne peut pas faire.
 * La vraie vérification est faite par le serveur sur chaque requête (voir backend/README.md, « Rôles »).
 */
const OWNER = 'owner';
const ADMIN = 'admin';
const ORDERS = 'order_manager';
const EDITOR = 'content_editor';
const ANALYST = 'analyst';

const RULES = {
  viewDashboard: [OWNER, ADMIN, ORDERS, ANALYST],
  viewOrders: [OWNER, ADMIN, ORDERS, ANALYST],
  manageOrders: [OWNER, ADMIN, ORDERS],
  viewCustomers: [OWNER, ADMIN, ORDERS, ANALYST],
  manageCustomers: [OWNER, ADMIN, ORDERS],
  viewInventory: [OWNER, ADMIN, ORDERS, EDITOR, ANALYST],
  adjustStock: [OWNER, ADMIN, ORDERS],
  viewSettings: [OWNER, ADMIN, ORDERS, ANALYST],
  editSettings: [OWNER, ADMIN],
};

export function can(user, action) {
  return Boolean(user?.role && RULES[action]?.includes(user.role));
}

/** Première page accessible après connexion. */
export function homePath(user) {
  return can(user, 'viewDashboard') ? '/admin/dashboard' : '/admin/inventory';
}
