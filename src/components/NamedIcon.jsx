import { getIcon } from '../utils/icons.js';

/** Affiche l'icône correspondant à un nom venant des données (ex. 'leaf'). */
export default function NamedIcon({ name, ...props }) {
  const Icon = getIcon(name);
  return <Icon {...props} />;
}
