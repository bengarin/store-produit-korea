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
  viewProducts: [OWNER, ADMIN, ORDERS, EDITOR, ANALYST],
  editProducts: [OWNER, ADMIN, EDITOR],
  deleteProducts: [OWNER, ADMIN],
  // Menu « Catégories » de la boutique : réservé aux administrateurs.
  manageCategories: [OWNER, ADMIN],
  // Filtres de la page produits (groupes et valeurs) : administrateurs ; cocher les valeurs d'un produit : editProducts.
  manageFilters: [OWNER, ADMIN],
  editCost: [OWNER, ADMIN],
  editSettings: [OWNER, ADMIN],
  // Phase 6 : thème. Lecture : toute l'équipe ; brouillon : + Éditeur ; publier / restaurer : Propriétaire, Admin.
  viewTheme: [OWNER, ADMIN, ORDERS, EDITOR, ANALYST],
  editTheme: [OWNER, ADMIN, EDITOR],
  publishTheme: [OWNER, ADMIN],
  viewNewsletter: [OWNER, ADMIN],
  // Blog : toute l'équipe lit ; écriture : + Éditeur ; suppression : Propriétaire, Admin.
  viewBlog: [OWNER, ADMIN, ORDERS, EDITOR, ANALYST],
  editBlog: [OWNER, ADMIN, EDITOR],
  deleteBlog: [OWNER, ADMIN],
  // Avis sur la boutique : modération (approuver, corriger, dépublier) : + Éditeur ; suppression : Propriétaire, Admin.
  viewReviews: [OWNER, ADMIN, ORDERS, EDITOR, ANALYST],
  moderateReviews: [OWNER, ADMIN, EDITOR],
  deleteReviews: [OWNER, ADMIN],
};

export function can(user, action) {
  return Boolean(user?.role && RULES[action]?.includes(user.role));
}

/** Première page accessible après connexion. */
export function homePath(user) {
  return can(user, 'viewDashboard') ? '/admin/dashboard' : '/admin/products';
}
