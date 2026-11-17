/**
 * Contrat des routes REST attendues du futur backend (voir docs/BACKEND.md).
 * Aucune de ces routes n'existe encore : elles ne sont appelées que si
 * VITE_API_BASE_URL est défini.
 */
export const ENDPOINTS = {
  products: '/products',
  product: (slug) => `/products/${encodeURIComponent(slug)}`,
  categories: '/categories',
  filters: '/filters',
  config: '/config',
  promoValidate: '/promo-codes/validate',
  orders: '/orders',
  theme: '/theme',
  newsletter: '/newsletter',
  blog: '/blog',
  blogArticle: (slug) => `/blog/${encodeURIComponent(slug)}`,
  reviews: '/reviews',
  productReviews: (slug) => `/products/${encodeURIComponent(slug)}/reviews`,
};
