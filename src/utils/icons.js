import { Droplets, Leaf, Sparkles, Sun, Citrus, Eye, Clock, Layers, FlaskConical, Hand, Circle } from 'lucide-react';

/**
 * Noms d'icônes autorisés dans les données produit (highlights[].icon).
 * Les données (locales ou API) contiennent un NOM ; l'interface choisit l'icône.
 */
const ICONS = {
  droplets: Droplets,
  leaf: Leaf,
  sparkles: Sparkles,
  sun: Sun,
  citrus: Citrus,
  eye: Eye,
  clock: Clock,
  layers: Layers,
  flask: FlaskConical,
  hand: Hand,
};

/** Icône associée à un nom ; icône neutre si le nom est inconnu. */
export const getIcon = (name) => ICONS[name] || Circle;
